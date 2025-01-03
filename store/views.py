# from flask import abort, redirect, request, url_for  # noqa
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm

# from flask_security.core import current_user


class AdminModelView(ModelView):
    """
    For Admin related views
    """

    # We want the form token
    form_base_class = SecureForm

    def is_accessible(self):
        # return (
        #     current_user.is_active
        #     and current_user.is_authenticated
        #     and (current_user.has_role("admin") or current_user.has_role("staff"))
        # )
        return True


class AppAdmin:
    form_widget_args = {
        "created_at": {
            "readonly": True,
        },
        "modified_at": {
            "readonly": True,
        },
    }
    page_size = 20
    can_create = True
    can_edit = True
    can_delete = True
    column_display_pk = True
    save_as = True
    save_as_continue = True
    can_export = True
    can_view_details = True
    can_set_page_size = True


class ProjectAdmin(AppAdmin, AdminModelView):
    name = "Project"
    name_plural = "Projects"
    icon = "bi-star"
    column_list = ["slug", "tags", "category", "supported_python"]

    @action(
        "fetch_data",
        "Fetch Project Data",
        "Fetch the latest data from their repositories. \nNote: no post-data processing in this stage.",
    )
    def action_fetch_data(self, ids):
        # projects = Project.query.filter(Project.id.in_(ids))
        # for project in projects.all():
        #     utils.fetch_project_info(project)
        #     flash(f"Data Retrieved: {project}", "info")
        pass
