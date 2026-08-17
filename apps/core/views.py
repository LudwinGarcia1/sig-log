from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import path, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView


class CrudConfig:
    """Declarative description of a standard maintenance module.

    Subclasses declare what varies (model, form, columns, labels) and inherit
    list, create, update and soft-delete behaviour. This is what keeps the
    seven capture modules at roughly forty lines each.
    """

    model = None
    form_class = None
    list_columns = []
    search_fields = []
    label = ""
    label_plural = ""
    slug = ""
    ordering = ("-created_at",)
    paginate_by = 20
    extra_actions = []

    @classmethod
    def as_context(cls):
        return {
            "crud_label": cls.label,
            "crud_label_plural": cls.label_plural,
            "crud_slug": cls.slug,
            "crud_columns": cls.list_columns,
            "crud_headers": [
                cls.model._meta.get_field(name).verbose_name
                for name in cls.list_columns
            ],
            "crud_searchable": bool(cls.search_fields),
            "crud_extra_actions": cls.extra_actions,
        }

    @classmethod
    def urlpatterns(cls):
        name = cls.model.__name__
        shared = {"crud": cls, "model": cls.model}
        with_form = dict(shared, form_class=cls.form_class)
        return [
            path(
                "",
                type(f"{name}ListView", (CrudListView,), dict(shared)).as_view(),
                name=f"{cls.slug}_list",
            ),
            path(
                "nuevo/",
                type(f"{name}CreateView", (CrudCreateView,), with_form).as_view(),
                name=f"{cls.slug}_create",
            ),
            path(
                "<int:pk>/editar/",
                type(f"{name}UpdateView", (CrudUpdateView,), with_form).as_view(),
                name=f"{cls.slug}_update",
            ),
            path(
                "<int:pk>/eliminar/",
                type(f"{name}DeleteView", (CrudDeleteView,), dict(shared)).as_view(),
                name=f"{cls.slug}_delete",
            ),
        ]


class CrudContextMixin:
    crud = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.crud.as_context())
        return context

    def get_success_url(self):
        return reverse_lazy(f"{self.crud.slug}_list")


class CrudListView(CrudContextMixin, ListView):
    template_name = "core/crud_list.html"
    context_object_name = "rows"

    def get_paginate_by(self, queryset):
        return self.crud.paginate_by

    def get_queryset(self):
        queryset = self.crud.model.objects.filter(is_active=True)
        term = self.request.GET.get("q", "").strip()
        if term and self.crud.search_fields:
            condition = Q()
            for field_name in self.crud.search_fields:
                condition |= Q(**{f"{field_name}__icontains": term})
            queryset = queryset.filter(condition)
        return queryset.order_by(*self.crud.ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_term"] = self.request.GET.get("q", "")
        return context


class CrudCreateView(CrudContextMixin, CreateView):
    template_name = "core/crud_form.html"

    def form_valid(self, form):
        messages.success(self.request, f"{self.crud.label} registrado correctamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = f"Nuevo {self.crud.label.lower()}"
        return context


class CrudUpdateView(CrudContextMixin, UpdateView):
    template_name = "core/crud_form.html"

    def form_valid(self, form):
        messages.success(self.request, f"{self.crud.label} actualizado correctamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_title"] = f"Editar {self.crud.label.lower()}"
        return context


class CrudDeleteView(CrudContextMixin, DeleteView):
    template_name = "core/crud_confirm_delete.html"

    def form_valid(self, form):
        self.object.deactivate()
        messages.success(self.request, f"{self.crud.label} dado de baja.")
        return redirect(self.get_success_url())


class HomeView(TemplateView):
    template_name = "core/home.html"
