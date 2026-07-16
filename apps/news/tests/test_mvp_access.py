import datetime as dt
import json
import re

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, RequestFactory
from django.urls import reverse
from wagtail.actions.publish_page_revision import (
    PublishPagePermissionError,
    PublishPageRevisionAction,
)
from wagtail.admin.views.pages.edit import EditView
from wagtail.images import get_image_model
from wagtail.models import (
    GroupCollectionPermission,
    GroupPagePermission,
    Task,
    Workflow,
    WorkflowPage,
    WorkflowState,
    WorkflowTask,
)

from apps.home.models import HomePage, InstitutionalPage
from apps.news.access import (
    DIRECTOR_GROUP_NAME,
    FINAL_REVIEW_TASK_NAME,
    FULL_EDITOR_PERMISSION,
    LEGACY_WORKFLOW_NAME,
    NEWS_SEO_FIELD_NAMES,
    SEO_CURATOR_GROUP_NAME,
    SEO_EDITOR_PERMISSION,
    SEO_TASK_NAME,
    WORKFLOW_NAME,
)
from apps.news.models import (
    ContributorGroup,
    MinorContributor,
    NewsPage,
    NewsPageContributor,
    NewsPagePublicCredit,
    NewsSection,
    School,
)

pytestmark = pytest.mark.django_db

GIF_BYTES = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
    b"\x00\x00\x02\x02D\x01\x00;"
)


def create_user(username: str, *group_names: str):
    user = get_user_model().objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-password",
    )
    user.groups.add(*Group.objects.filter(name__in=group_names))
    return user


def create_news_page(*, slug: str = "noticia-workflow") -> NewsPage:
    home = HomePage.objects.get()
    page = NewsPage(
        title="Noticia ficticia para workflow",
        slug=slug,
        live=False,
        publication_date=dt.date(2026, 7, 15),
        summary="Resumen editorial original y protegido.",
        body=[("paragraph", "<p>Contenido editorial ficticio y seguro.</p>")],
        section=NewsSection.objects.get(slug="politica"),
        coverage_province="Arequipa",
    )
    home.add_child(instance=page)
    NewsPagePublicCredit.objects.create(page=page, display_name="Redacción escolar")
    page.save_revision()
    return page


def create_institutional_page() -> InstitutionalPage:
    page = InstitutionalPage(
        title="Institucional workflow",
        slug="institucional-workflow",
        live=False,
        introduction="Introducción editorial protegida.",
        body="<p>Contenido institucional protegido.</p>",
    )
    HomePage.objects.get().add_child(instance=page)
    page.save_revision()
    return page


def bootstrap_access() -> None:
    call_command("bootstrap_mvp_access", verbosity=0)


def seo_workflow_action_data(page: NewsPage, action: str, comment: str = ""):
    return {
        "slug": page.slug,
        "seo_title": page.seo_title,
        "search_description": page.search_description,
        "focus_keyphrase": page.focus_keyphrase,
        "og_title": page.og_title,
        "og_description": page.og_description,
        "og_image_caption": page.og_image_caption,
        "og_image_alt_text": page.og_image_alt_text,
        "og_image_credit": page.og_image_credit,
        "canonical_url": page.canonical_url,
        "action-workflow-action": "1",
        "workflow-action-name": action,
        "workflow-action-extra-data": json.dumps({"comment": comment}),
    }


def start_workflow(page: NewsPage | InstitutionalPage, user):
    page.save_revision(user=user)
    return page.get_workflow().start(page, user)


def visible_tab_labels(response) -> list[str]:
    return [
        label.strip()
        for label in re.findall(
            r'<a id="tab-label-[^"]+"[^>]*role="tab"[^>]*>\s*([^<]+)',
            response.content.decode(),
        )
    ]


def test_bootstrap_is_idempotent_and_preserves_unrelated_objects() -> None:
    unrelated_task = Task.objects.create(name="Tarea no relacionada")
    unrelated_workflow = Workflow.objects.create(name="Flujo no relacionado")

    bootstrap_access()
    first_task_ids = set(
        Task.objects.filter(
            name__in=[SEO_TASK_NAME, FINAL_REVIEW_TASK_NAME]
        ).values_list("pk", flat=True)
    )
    first_workflow_id = Workflow.objects.get(name=WORKFLOW_NAME).pk

    bootstrap_access()

    assert Group.objects.filter(name=DIRECTOR_GROUP_NAME).count() == 1
    assert Group.objects.filter(name=SEO_CURATOR_GROUP_NAME).count() == 1
    assert Task.objects.filter(name=SEO_TASK_NAME).count() == 1
    assert Task.objects.filter(name=FINAL_REVIEW_TASK_NAME).count() == 1
    assert Workflow.objects.filter(name=WORKFLOW_NAME).count() == 1
    assert (
        set(
            Task.objects.filter(
                name__in=[SEO_TASK_NAME, FINAL_REVIEW_TASK_NAME]
            ).values_list("pk", flat=True)
        )
        == first_task_ids
    )
    assert Workflow.objects.get(name=WORKFLOW_NAME).pk == first_workflow_id
    assert Task.objects.filter(pk=unrelated_task.pk).exists()
    assert Workflow.objects.filter(pk=unrelated_workflow.pk).exists()
    assert not Group.objects.filter(name__in=["Moderadores", "Editores"]).exists()


def test_bootstrap_renames_the_owned_legacy_workflow_in_place() -> None:
    legacy_workflow = Workflow.objects.create(name=LEGACY_WORKFLOW_NAME)

    bootstrap_access()

    renamed_workflow = Workflow.objects.get(name=WORKFLOW_NAME)
    assert renamed_workflow.pk == legacy_workflow.pk
    assert not Workflow.objects.filter(name=LEGACY_WORKFLOW_NAME).exists()


def test_bootstrap_assigns_existing_users_without_creating_credentials() -> None:
    director = create_user("director-bootstrap")
    curator = create_user("curator-bootstrap")
    combined = create_user("combined-bootstrap")

    call_command(
        "bootstrap_mvp_access",
        "--director",
        director.username,
        "--seo-curator",
        curator.username,
        "--combined-user",
        combined.username,
        verbosity=0,
    )

    assert director.groups.filter(name=DIRECTOR_GROUP_NAME).exists()
    assert curator.groups.filter(name=SEO_CURATOR_GROUP_NAME).exists()
    assert set(combined.groups.values_list("name", flat=True)) == {
        DIRECTOR_GROUP_NAME,
        SEO_CURATOR_GROUP_NAME,
    }
    assert get_user_model().objects.count() == 3


def test_bootstrap_configures_exact_group_permission_boundaries() -> None:
    bootstrap_access()
    home = HomePage.objects.get()
    director_group = Group.objects.get(name=DIRECTOR_GROUP_NAME)
    seo_group = Group.objects.get(name=SEO_CURATOR_GROUP_NAME)

    director_global_permissions = set(
        director_group.permissions.values_list("codename", flat=True)
    )
    seo_global_permissions = set(
        seo_group.permissions.values_list("codename", flat=True)
    )
    assert {"access_admin", "access_full_editorial_surfaces"} <= (
        director_global_permissions
    )
    assert "access_seo_editorial_surface" in director_global_permissions
    assert "change_minorcontributor" in director_global_permissions
    assert seo_global_permissions == {
        "access_admin",
        "access_seo_editorial_surface",
    }

    assert set(
        GroupPagePermission.objects.filter(group=director_group).values_list(
            "page_id", "permission__codename"
        )
    ) == {
        (home.pk, "add_page"),
        (home.pk, "change_page"),
        (home.pk, "publish_page"),
    }
    assert not GroupPagePermission.objects.filter(group=seo_group).exists()
    assert set(
        GroupCollectionPermission.objects.filter(group=director_group).values_list(
            "permission__codename", flat=True
        )
    ) == {
        "add_document",
        "add_image",
        "change_document",
        "change_image",
        "choose_document",
        "choose_image",
    }
    assert set(
        GroupCollectionPermission.objects.filter(group=seo_group).values_list(
            "permission__codename", flat=True
        )
    ) == {"choose_image"}


def test_director_and_seo_curator_real_permission_matrix() -> None:
    bootstrap_access()
    page = create_news_page()
    director = create_user("director-matrix", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-matrix", SEO_CURATOR_GROUP_NAME)

    assert not director.is_superuser
    assert director.has_perm("wagtailadmin.access_admin")
    assert director.has_perm(FULL_EDITOR_PERMISSION)
    assert director.has_perm(SEO_EDITOR_PERMISSION)
    assert page.permissions_for_user(director).can_edit()
    assert page.permissions_for_user(director).can_publish()
    assert director.has_perm("news.change_minorcontributor")
    assert not director.has_perm("auth.change_user")
    assert not director.has_perm("auth.change_group")

    assert not curator.is_superuser
    assert curator.has_perm("wagtailadmin.access_admin")
    assert not curator.has_perm(FULL_EDITOR_PERMISSION)
    assert curator.has_perm(SEO_EDITOR_PERMISSION)
    assert not page.permissions_for_user(curator).can_edit()
    assert not page.permissions_for_user(curator).can_publish()
    assert not curator.has_perm("news.view_minorcontributor")
    assert not curator.has_perm("news.change_newssection")
    assert not curator.has_perm("auth.change_user")
    assert not curator.has_perm("auth.change_group")

    director_client = Client()
    director_client.force_login(director)
    curator_client = Client()
    curator_client.force_login(curator)
    assert director_client.get(reverse("wagtailadmin_home")).status_code == 200
    assert curator_client.get(reverse("wagtailadmin_home")).status_code == 200
    assert (
        director_client.get(
            reverse("wagtailsnippets_news_minorcontributor:list")
        ).status_code
        == 200
    )
    assert (
        curator_client.get(
            reverse("wagtailsnippets_news_minorcontributor:list")
        ).status_code
        != 200
    )
    assert director_client.get("/admin/users/").status_code != 200
    assert curator_client.get("/admin/users/").status_code != 200


def test_role_bound_forms_expose_only_authorized_fields_and_relations() -> None:
    bootstrap_access()
    page = create_news_page()
    director = create_user("director-form", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-form", SEO_CURATOR_GROUP_NAME)
    form_class = NewsPage.get_edit_handler().get_form_class()

    director_form = form_class(
        instance=page,
        parent_page=page.get_parent(),
        for_user=director,
    )
    curator_form = form_class(
        instance=page,
        parent_page=page.get_parent(),
        for_user=curator,
    )

    assert NEWS_SEO_FIELD_NAMES < set(director_form.fields)
    assert {"body", "show_in_menus", "contains_identifiable_minors"} <= set(
        director_form.fields
    )
    assert {"comments", "internal_contributors", "public_credits"} == set(
        director_form.formsets
    )
    assert set(curator_form.fields) == NEWS_SEO_FIELD_NAMES
    assert curator_form.formsets == {}


def test_seo_curator_edit_surface_hides_content_properties_and_minor_data() -> None:
    bootstrap_access()
    page = create_news_page()
    image = get_image_model().objects.create(
        title="Imagen ficticia para contexto SEO",
        file=SimpleUploadedFile(
            "contexto-seo.gif",
            GIF_BYTES,
            content_type="image/gif",
        ),
    )
    page.featured_image = image
    page.featured_image_caption = "Taller ficticio preparando una noticia."
    page.featured_image_alt_text = "Cuadernos y grabadoras sobre una mesa."
    page.featured_image_credit = "Archivo escolar ficticio"
    page.save()
    school = School.objects.create(
        name="Colegio ficticio interno",
        province="Arequipa",
        district="Cercado",
    )
    contributor_group = ContributorGroup.objects.create(
        name="Taller interno ficticio",
        school=school,
    )
    internal_contributor = MinorContributor.objects.create(
        full_name="Nombre privado que no debe mostrarse",
        group=contributor_group,
        age_band=MinorContributor.AgeBand.UNDER_14,
    )
    NewsPageContributor.objects.create(
        page=page,
        contributor=internal_contributor,
    )
    director = create_user("director-surface", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-surface", SEO_CURATOR_GROUP_NAME)
    start_workflow(page, director)
    client = Client()
    client.force_login(curator)

    response = client.get(reverse("wagtailadmin_pages:edit", args=(page.pk,)))
    content = response.content.decode()
    context_fragment = content.split(
        "Contexto de la noticia — solo lectura",
        maxsplit=1,
    )[1].split("Configuración SEO", maxsplit=1)[0]

    assert response.status_code == 200
    assert visible_tab_labels(response) == ["Asistente SEO"]
    assert 'name="seo_title"' in content
    assert 'name="og_image"' in content
    assert 'name="summary"' not in content
    assert 'name="body"' not in content
    assert 'name="show_in_menus"' not in content
    assert 'name="contains_identifiable_minors"' not in content
    assert "Colaboradores internos" not in content
    assert "Propiedades" not in visible_tab_labels(response)
    assert "Publicar" not in content
    assert "Contexto de la noticia — solo lectura" in content
    assert "Noticia ficticia para workflow" in content
    assert "Política" in context_fragment, context_fragment
    assert "15 de julio de 2026" in content
    assert "Resumen editorial original y protegido." in content
    assert "Contenido editorial ficticio y seguro." in content
    assert "Taller ficticio preparando una noticia." in content
    assert "Cuadernos y grabadoras sobre una mesa." in content
    assert "Archivo escolar ficticio" in content
    assert "Redacción escolar" in content
    assert "Previsualizar borrador completo" in content
    assert reverse("wagtailadmin_pages:view_draft", args=(page.pk,)) in content
    assert "Nombre privado que no debe mostrarse" not in content
    assert "Menor de 14 años" not in content
    assert "Privacidad de menores" not in content
    assert "autorizaciones requeridas" not in content
    assert "<input" not in context_fragment
    assert "<textarea" not in context_fragment
    assert "<select" not in context_fragment


def test_seo_curator_manipulated_post_cannot_change_non_seo_fields() -> None:
    bootstrap_access()
    page = create_news_page(slug="noticia-post-protegido")
    school = School.objects.create(
        name="Colegio ficticio",
        province="Arequipa",
        district="Cercado",
    )
    contributor_group = ContributorGroup.objects.create(
        name="Taller ficticio",
        school=school,
    )
    contributor = MinorContributor.objects.create(
        full_name="Nombre interno ficticio",
        group=contributor_group,
        age_band=MinorContributor.AgeBand.UNDER_14,
    )
    NewsPageContributor.objects.create(page=page, contributor=contributor)
    director = create_user("director-post", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-post", SEO_CURATOR_GROUP_NAME)
    start_workflow(page, director)
    client = Client()
    client.force_login(curator)

    response = client.post(
        reverse("wagtailadmin_pages:edit", args=(page.pk,)),
        {
            "slug": page.slug,
            "seo_title": "Título SEO autorizado",
            "search_description": "Descripción SEO autorizada.",
            "focus_keyphrase": "frase ficticia",
            "og_title": "Título social autorizado",
            "og_description": "Descripción social autorizada.",
            "canonical_url": "",
            "seo_noindex": "",
            "summary": "RESUMEN MANIPULADO",
            "title": "TÍTULO MANIPULADO",
            "body": "CONTENIDO MANIPULADO",
            "show_in_menus": "on",
            "contains_identifiable_minors": "on",
            "internal_contributors-TOTAL_FORMS": "0",
            "internal_contributors-INITIAL_FORMS": "0",
            "action-save": "Guardar borrador",
        },
    )

    assert response.status_code == 302
    saved_page = NewsPage.objects.get(pk=page.pk).get_latest_revision_as_object()
    assert saved_page.seo_title == "Título SEO autorizado"
    assert saved_page.summary == "Resumen editorial original y protegido."
    assert saved_page.title == "Noticia ficticia para workflow"
    assert "CONTENIDO MANIPULADO" not in str(saved_page.body)
    assert not saved_page.show_in_menus
    assert not saved_page.contains_identifiable_minors
    saved_contributor_ids = saved_page.internal_contributors.values_list(
        "contributor_id",
        flat=True,
    )
    assert list(saved_contributor_ids) == [contributor.pk]


def test_native_workflow_order_final_publication_and_request_changes() -> None:
    bootstrap_access()
    page = create_news_page()
    director = create_user("director-workflow", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-workflow", SEO_CURATOR_GROUP_NAME)
    workflow = Workflow.objects.get(name=WORKFLOW_NAME)

    assert list(
        WorkflowTask.objects.filter(workflow=workflow)
        .order_by("sort_order")
        .values_list("task__name", flat=True)
    ) == [SEO_TASK_NAME, FINAL_REVIEW_TASK_NAME]

    rejected_state = start_workflow(page, director)
    seo_task = rejected_state.current_task_state.task.specific
    seo_task.on_action(
        rejected_state.current_task_state,
        curator,
        "reject",
        comment="Ajustar la descripción meta.",
    )
    rejected_state.refresh_from_db()
    assert rejected_state.status == WorkflowState.STATUS_NEEDS_CHANGES
    rejected_state.resume(user=director)
    rejected_state.refresh_from_db()
    assert rejected_state.current_task_state.task.name == SEO_TASK_NAME
    rejected_state.cancel(user=director)

    state = start_workflow(page, director)
    state.current_task_state.task.specific.on_action(
        state.current_task_state,
        curator,
        "approve",
    )
    state.refresh_from_db()
    assert state.current_task_state.task.name == FINAL_REVIEW_TASK_NAME
    assert state.current_task_state.task.specific.get_actions(page, curator) == []
    assert not NewsPage.objects.get(pk=page.pk).live

    state.current_task_state.task.specific.on_action(
        state.current_task_state,
        director,
        "approve",
    )
    state.refresh_from_db()
    assert state.status == WorkflowState.STATUS_APPROVED
    assert NewsPage.objects.get(pk=page.pk).live


def test_unauthorized_group_cannot_approve_other_groups_task() -> None:
    bootstrap_access()
    page = create_news_page()
    director = create_user("director-boundary", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-boundary", SEO_CURATOR_GROUP_NAME)
    outsider = create_user("workflow-outsider")
    state = start_workflow(page, director)
    seo_task = state.current_task_state.task.specific

    assert seo_task.get_actions(page, curator)
    assert seo_task.get_actions(page, director) == []
    assert seo_task.get_actions(page, outsider) == []

    request = RequestFactory().post(
        "/admin/pages/action/",
        {"workflow-action-name": "approve"},
    )
    request.user = outsider
    view = EditView()
    view.request = request
    view.page = page
    assert not view.workflow_action_is_valid()
    state.refresh_from_db()
    assert state.current_task_state.task.name == SEO_TASK_NAME


def test_combined_non_superuser_can_complete_both_workflow_tasks() -> None:
    bootstrap_access()
    page = create_news_page()
    combined = create_user(
        "combined-workflow",
        DIRECTOR_GROUP_NAME,
        SEO_CURATOR_GROUP_NAME,
    )
    state = start_workflow(page, combined)

    for expected_task_name in (SEO_TASK_NAME, FINAL_REVIEW_TASK_NAME):
        state.refresh_from_db()
        assert state.current_task_state.task.name == expected_task_name
        assert state.current_task_state.task.specific.get_actions(page, combined)
        state.current_task_state.task.specific.on_action(
            state.current_task_state,
            combined,
            "approve",
        )

    state.refresh_from_db()
    assert state.status == WorkflowState.STATUS_APPROVED
    assert NewsPage.objects.get(pk=page.pk).live


def test_director_direct_publish_override_and_curator_publish_denial() -> None:
    bootstrap_access()
    page = create_news_page()
    director = create_user("director-publish", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-publish", SEO_CURATOR_GROUP_NAME)
    revision = page.get_latest_revision()

    with pytest.raises(PublishPagePermissionError):
        PublishPageRevisionAction(revision, user=curator).execute()

    PublishPageRevisionAction(revision, user=director).execute()
    assert NewsPage.objects.get(pk=page.pk).live


def test_workflow_assignment_covers_inicio_and_all_native_descendant_types() -> None:
    bootstrap_access()
    home = HomePage.objects.get()
    news = create_news_page()
    institutional = create_institutional_page()
    workflow = Workflow.objects.get(name=WORKFLOW_NAME)

    assert WorkflowPage.objects.get(page=home).workflow == workflow
    assert home.get_workflow() == workflow
    assert news.get_workflow() == workflow
    assert institutional.get_workflow() == workflow
    assert home.get_parent().get_workflow() != workflow


def test_rendered_workflow_labels_match_the_documented_editor_actions() -> None:
    bootstrap_access()
    page = create_news_page(slug="noticia-etiquetas-workflow")
    director = create_user("director-labels", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-labels", SEO_CURATOR_GROUP_NAME)
    director_client = Client()
    director_client.force_login(director)

    draft_response = director_client.get(
        reverse("wagtailadmin_pages:edit", args=(page.pk,))
    )
    draft_content = draft_response.content.decode()
    assert "Enviar a Revisión editorial" in draft_content
    assert "Enviar para ser moderado" not in draft_content

    state = start_workflow(page, director)
    state.current_task_state.task.specific.on_action(
        state.current_task_state,
        curator,
        "approve",
    )
    final_response = director_client.get(
        reverse("wagtailadmin_pages:edit", args=(page.pk,))
    )
    final_content = final_response.content.decode()

    for label in (
        "Publicar",
        "Cancelar flujo de trabajo",
        "Solicitar cambios",
        "Aprobar y Publicar",
        "Aprobar con comentario y Publicar",
        "Guardar borrador",
    ):
        assert label in final_content


@pytest.mark.parametrize(
    ("action", "expected_status", "expected_task_name"),
    [
        ("reject", WorkflowState.STATUS_NEEDS_CHANGES, SEO_TASK_NAME),
        ("approve", WorkflowState.STATUS_IN_PROGRESS, FINAL_REVIEW_TASK_NAME),
    ],
)
def test_seo_workflow_action_redirects_to_dashboard_after_edit_access_ends(
    action,
    expected_status,
    expected_task_name,
) -> None:
    bootstrap_access()
    page = create_news_page(slug=f"noticia-redireccion-{action}")
    director = create_user(f"director-redirect-{action}", DIRECTOR_GROUP_NAME)
    curator = create_user(f"curator-redirect-{action}", SEO_CURATOR_GROUP_NAME)
    state = start_workflow(page, director)
    client = Client()
    client.force_login(curator)

    response = client.post(
        reverse("wagtailadmin_pages:edit", args=(page.pk,)),
        seo_workflow_action_data(
            page,
            action,
            comment="Ajuste ficticio solicitado." if action == "reject" else "",
        ),
        follow=True,
    )

    state.refresh_from_db()
    content = response.content.decode()
    assert response.redirect_chain == [(reverse("wagtailadmin_home"), 302)]
    assert response.status_code == 200
    assert state.status == expected_status
    assert state.current_task_state.task.name == expected_task_name
    assert "Noticia ficticia para workflow" in content
    assert re.search(r'<li[^>]*class="[^"]*\bsuccess\b', content)
    assert "No tienes permiso" not in content
    assert "You do not have permission" not in content


def test_workflow_dashboard_headings_are_precisely_translated() -> None:
    bootstrap_access()
    page = create_news_page(slug="noticia-dashboard-traducido")
    director = create_user("director-dashboard", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-dashboard", SEO_CURATOR_GROUP_NAME)
    start_workflow(page, director)
    director_client = Client()
    director_client.force_login(director)
    curator_client = Client()
    curator_client.force_login(curator)

    director_response = director_client.get(reverse("wagtailadmin_home"))
    curator_response = curator_client.get(reverse("wagtailadmin_home"))
    director_content = director_response.content.decode()
    curator_content = curator_response.content.decode()

    assert director_response.status_code == 200
    assert curator_response.status_code == 200
    assert "Tus páginas y elementos editoriales en flujo de trabajo" in (
        director_content
    )
    assert "Pendientes de tu revisión" in curator_content
    assert "Privacidad y acceso" in director_content
    assert "Privacidad y acceso" in curator_content
    assert "Your pages and snippets in a workflow" not in director_content
    assert "Awaiting your review" not in curator_content


def test_institutional_seo_task_exposes_native_seo_fields_only() -> None:
    bootstrap_access()
    page = create_institutional_page()
    director = create_user("director-institutional", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-institutional", SEO_CURATOR_GROUP_NAME)
    start_workflow(page, director)
    client = Client()
    client.force_login(curator)

    response = client.get(reverse("wagtailadmin_pages:edit", args=(page.pk,)))
    content = response.content.decode()

    assert response.status_code == 200
    assert visible_tab_labels(response) == ["Asistente SEO"]
    assert 'name="slug"' in content
    assert 'name="seo_title"' in content
    assert 'name="search_description"' in content
    assert 'name="title"' not in content
    assert 'name="introduction"' not in content
    assert 'name="body"' not in content
    assert 'name="show_in_menus"' not in content
    assert "Contexto de la página — solo lectura" in content
    assert "Institucional workflow" in content
    assert "Previsualizar borrador completo" in content
    assert reverse("wagtailadmin_pages:view_draft", args=(page.pk,)) in content


def test_institutional_seo_crafted_post_cannot_change_read_only_context() -> None:
    bootstrap_access()
    page = create_institutional_page()
    director = create_user("director-institutional-post", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-institutional-post", SEO_CURATOR_GROUP_NAME)
    start_workflow(page, director)
    client = Client()
    client.force_login(curator)

    response = client.post(
        reverse("wagtailadmin_pages:edit", args=(page.pk,)),
        {
            "slug": page.slug,
            "seo_title": "Título SEO institucional autorizado",
            "search_description": "Descripción institucional autorizada.",
            "title": "TÍTULO INSTITUCIONAL MANIPULADO",
            "introduction": "INTRODUCCIÓN MANIPULADA",
            "body": "CUERPO MANIPULADO",
            "show_in_menus": "on",
            "action-save": "Guardar borrador",
        },
    )

    assert response.status_code == 302
    saved_page = InstitutionalPage.objects.get(
        pk=page.pk
    ).get_latest_revision_as_object()
    assert saved_page.seo_title == "Título SEO institucional autorizado"
    assert saved_page.title == "Institucional workflow"
    assert saved_page.introduction == "Introducción editorial protegida."
    assert "CUERPO MANIPULADO" not in str(saved_page.body)
    assert not saved_page.show_in_menus


def test_home_seo_task_provides_read_only_context_and_draft_preview() -> None:
    bootstrap_access()
    page = HomePage.objects.get()
    director = create_user("director-home", DIRECTOR_GROUP_NAME)
    curator = create_user("curator-home", SEO_CURATOR_GROUP_NAME)
    start_workflow(page, director)
    client = Client()
    client.force_login(curator)

    response = client.get(reverse("wagtailadmin_pages:edit", args=(page.pk,)))
    content = response.content.decode()

    assert response.status_code == 200
    assert visible_tab_labels(response) == ["Asistente SEO"]
    assert "Contexto de la página — solo lectura" in content
    assert page.title in content
    assert "Previsualizar borrador completo" in content
    assert reverse("wagtailadmin_pages:view_draft", args=(page.pk,)) in content
    assert 'name="slug"' in content
    assert 'name="seo_title"' in content
    assert 'name="search_description"' in content
    assert 'name="title"' not in content
    assert 'name="show_in_menus"' not in content
