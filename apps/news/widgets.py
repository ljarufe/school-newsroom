from django import forms


class TaxonomyTreeWidget(forms.CheckboxSelectMultiple):
    template_name = "news/widgets/taxonomy_tree.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sections = []
        self.has_taxonomy_error = False

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        selected_values = {str(item) for item in value or []}
        children_by_parent: dict[int, list] = {}
        roots = []
        for section in self.sections:
            if section.parent_id is None:
                roots.append(section)
            else:
                children_by_parent.setdefault(section.parent_id, []).append(section)

        base_id = context["widget"]["attrs"].get("id", f"id_{name}")
        input_attrs = {
            key: attr_value
            for key, attr_value in context["widget"]["attrs"].items()
            if key != "id"
        }
        nodes = []
        for root in roots:
            children = children_by_parent.get(root.pk, [])
            expanded = (
                self.has_taxonomy_error
                or str(root.pk) in selected_values
                or any(str(child.pk) in selected_values for child in children)
            )
            nodes.append(
                {
                    "root": root,
                    "children": children,
                    "expanded": expanded,
                    "root_checked": str(root.pk) in selected_values,
                    "child_values": selected_values,
                    "branch_id": f"{base_id}-branch-{root.pk}",
                    "root_input_id": f"{base_id}-{root.pk}",
                    "children_with_ids": [
                        (child, f"{base_id}-{child.pk}") for child in children
                    ],
                }
            )
        context["widget"].update(nodes=nodes, has_error=self.has_taxonomy_error)
        context["widget"]["attrs"] = input_attrs
        return context
