"""
Views for the Products application.

This module handles the creation, editing, listing, and management of product-related entities
such as categories, product templates, configurations, and instances. It also provides
API endpoints for dynamic interactions.
"""

from __future__ import annotations
import json
from typing import Any, Dict

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import (
    Categoria, Atributo, Componente, ProdutoTemplate, ProdutoInstancia,
    ProdutoConfiguracao, TemplateAtributo, ConfiguracaoComponenteEscolha,
    InstanciaAtributo, InstanciaComponente, TemplateComponente
)
from orcamentos.models import ItemOrcamento, Orcamento # Assuming these are needed for related lookups
from .forms import (
    CategoriaForm, AtributoForm, ProdutoTemplateForm, ProdutoInstanciaForm,
    TemplateAtributoFormSet, ProdutoConfiguracaoForm,
    ConfiguracaoComponenteEscolhaFormSet, InstanciaAtributoFormSet,
    InstanciaComponenteFormSet
)


# =============================================================================
# HTML Rendering Views
# =============================================================================

def produtos_home(request: HttpRequest) -> HttpResponse:
    """
    Renders the main home page for the products module.

    Args:
        request: The HttpRequest object.

    Returns:
        An HttpResponse object rendering the products home page.
    """
    return render(request, 'produtos/produtos_home.html')


def listar_categorias(request: HttpRequest) -> HttpResponse:
    """
    Lists all product categories.

    Args:
        request: The HttpRequest object.

    Returns:
        An HttpResponse object rendering the list of categories.
    """
    categorias = Categoria.objects.all()
    context = {'categorias': categorias}
    return render(request, 'produtos/listar_categorias.html', context)


def criar_categoria(request: HttpRequest) -> HttpResponse:
    """
    Handles the creation of a new product category.

    On GET, it displays an empty form. On POST, it validates the form data
    and saves a new Categoria object if valid.

    Args:
        request: The HttpRequest object.

    Returns:
        An HttpResponse object, either rendering the form or redirecting
        to the category list upon successful creation.
    """
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Categoria criada com sucesso!"))
            return redirect('listar_categorias')
        else:
            messages.error(
                request, _("Erro ao criar categoria. Verifique os dados."))
    else:
        form = CategoriaForm()
    context = {'form': form}
    return render(request, 'produtos/criar_categoria.html', context)


def detalhes_categoria(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Displays the details of a specific category.

    Args:
        request: The HttpRequest object.
        pk: The primary key of the Categoria to display.

    Returns:
        An HttpResponse object rendering the category details page.
    """
    categoria = get_object_or_404(Categoria, pk=pk)
    context = {'categoria': categoria}
    return render(request, 'produtos/detalhes_categoria.html', context)


def listar_produtos_template(request: HttpRequest) -> HttpResponse:
    """
    Lists all product templates, with optional filtering by name or category.

    Args:
        request: The HttpRequest object. Supports GET parameter 'q' for search.

    Returns:
        An HttpResponse object rendering the list of product templates.
    """
    produtos_template = ProdutoTemplate.objects.all()

    query = request.GET.get('q')
    if query:
        produtos_template = produtos_template.filter(
            Q(nome__icontains=query) |
            Q(categoria__nome__icontains=query)
        ).distinct()

    context = {'produtos_template': produtos_template, 'query': query}
    return render(request, 'produtos/listar_produtos_template.html', context)


def criar_produto_template(request: HttpRequest) -> HttpResponse:
    """
    Handles the creation of a new product template.

    On GET, displays an empty form and an empty formset for attributes.
    On POST, validates and saves the new template and its associated attributes.

    Args:
        request: The HttpRequest object.

    Returns:
        An HttpResponse object, either rendering the form or redirecting
        to the template list upon successful creation.
    """
    if request.method == 'POST':
        form = ProdutoTemplateForm(request.POST)
        formset = TemplateAtributoFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            produto_template = form.save()
            # Associate the formset instances with the newly created template
            formset.instance = produto_template
            formset.save()
            messages.success(request, _("Template de Produto criado com sucesso!"))
            return redirect('listar_produtos_template')
        else:
            messages.error(
                request, _("Erro ao criar Template de Produto. Verifique os dados e os atributos."))
    else:
        form = ProdutoTemplateForm()
        formset = TemplateAtributoFormSet()
    context = {'form': form, 'formset': formset}
    return render(request, 'produtos/criar_produto_template.html', context)


def listar_produto_instancias(request: HttpRequest) -> HttpResponse:
    """
    Lists all product instances with filtering capabilities.

    Filters can be applied for a search query, category, or budget name.

    Args:
        request: The HttpRequest object. Supports GET parameters 'q',
                 'categoria', and 'orcamento_nome'.

    Returns:
        An HttpResponse object rendering the list of product instances.
    """
    instancias = ProdutoInstancia.objects.select_related(
        'configuracao__template__categoria'
    ).prefetch_related(
        'itemorcamento_set__orcamento' # Assuming a reverse relation from ItemOrcamento to ProdutoInstancia
    ).all()

    categorias = Categoria.objects.all()

    query = request.GET.get('q')
    categoria_id = request.GET.get('categoria')
    orcamento_nome = request.GET.get('orcamento_nome')

    if query:
        instancias = instancias.filter(
            Q(codigo__icontains=query) |
            Q(configuracao__nome__icontains=query)
        ).distinct()

    if categoria_id:
        instancias = instancias.filter(configuracao__template__categoria__id=categoria_id)

    if orcamento_nome:
        instancias = instancias.filter(itemorcamento__orcamento__nome_cliente__icontains=orcamento_nome).distinct()

    context = {
        'instancias': instancias,
        'categorias': categorias,
        'query': query,
        'selected_categoria': int(categoria_id) if categoria_id else None,
        'orcamento_nome': orcamento_nome,
    }
    return render(request, 'produtos/listar_produto_instancias.html', context)


def listar_produto_configuracoes(request: HttpRequest) -> HttpResponse:
    """
    Lists all product configurations with filtering by name or category.

    Args:
        request: The HttpRequest object. Supports GET parameters 'q' and
                 'categoria'.

    Returns:
        An HttpResponse object rendering the list of product configurations.
    """
    configuracoes = ProdutoConfiguracao.objects.all()
    categorias = Categoria.objects.all() # Get all categories for the filter dropdown

    query = request.GET.get('q')
    categoria_id = request.GET.get('categoria')

    if query:
        configuracoes = configuracoes.filter(
            Q(nome__icontains=query) |
            Q(descricao__icontains=query) # Assuming ProdutoConfiguracao has a description field
        ).distinct()

    if categoria_id:
        configuracoes = configuracoes.filter(template__categoria__id=categoria_id)

    context = {
        'configuracoes': configuracoes,
        'categorias': categorias,
        'query': query,
        'selected_categoria': int(categoria_id) if categoria_id else None,
    }
    return render(request, 'produtos/listar_produto_configuracoes.html', context)


def criar_produto_configuracao(request: HttpRequest) -> HttpResponse:
    """
    Handles the creation of a new product configuration.

    On GET, it displays an empty form and a formset for component choices.
    On POST, it validates and saves the new configuration and its associated
    component choices.

    Args:
        request: The HttpRequest object.

    Returns:
        An HttpResponse object, either rendering the form or redirecting
        to the configuration list upon successful creation.
    """
    template_id = request.GET.get('template_id')
    template = None
    if template_id:
        template = get_object_or_404(ProdutoTemplate, pk=template_id)

    if request.method == 'POST':
        form = ProdutoConfiguracaoForm(request.POST)
        formset = ConfiguracaoComponenteEscolhaFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            produto_configuracao = form.save(commit=False)
            if template: # Assign template if it came from GET
                produto_configuracao.template = template
            produto_configuracao.save()

            formset.instance = produto_configuracao
            formset.save()

            messages.success(request, _("Configuração de Produto criada com sucesso!"))
            return redirect('listar_produto_configuracoes')
        else:
            messages.error(
                request, _("Erro ao criar Configuração de Produto. Verifique os dados e as escolhas de componentes."))
    else:
        initial_form_data = {}
        if template:
            initial_form_data['template'] = template.id
        form = ProdutoConfiguracaoForm(initial=initial_form_data)
        # Ensure the template field is not disabled if it was pre-filled
        # form.fields['template'].queryset = ProdutoTemplate.objects.all()
        formset = ConfiguracaoComponenteEscolhaFormSet()

    context = {
        'form': form,
        'formset': formset,
        'template': template, # Pass template to context for template rendering
    }
    return render(request, 'produtos/criar_produto_configuracao.html', context)


def editar_produto_configuracao(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Handles editing a product configuration and its component choices.

    On GET, displays the form for the configuration and a formset for its
    component choices. On POST, validates and saves the changes.

    Args:
        request: The HttpRequest object.
        pk: The primary key of the ProdutoConfiguracao to edit.

    Returns:
        An HttpResponse object, either rendering the form or redirecting
        to the configuration list upon successful update.
    """
    configuracao = get_object_or_404(ProdutoConfiguracao, pk=pk)
    template = configuracao.template # Get the template from the existing configuration

    # Prepare initial data for ConfiguracaoComponenteEscolhaFormSet
    # This is used to pre-fill the formset with existing choices
    initial_component_choices_data = {}
    for cce in configuracao.componentes_escolha.all():
        initial_component_choices_data[cce.template_componente.id] = {
            'id': cce.id,
            'componente_real_id': cce.componente_real.id,
        }

    if request.method == 'POST':
        form = ProdutoConfiguracaoForm(request.POST, instance=configuracao)
        formset = ConfiguracaoComponenteEscolhaFormSet(request.POST, request.FILES, instance=configuracao)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, _("Configuração de Produto atualizada com sucesso!"))
            return redirect('listar_produto_configuracoes')
        else:
            messages.error(
                request, _("Erro ao atualizar Configuração de Produto. Verifique os dados e as escolhas de componentes."))
    else:
        form = ProdutoConfiguracaoForm(instance=configuracao)
        formset = ConfiguracaoComponenteEscolhaFormSet(instance=configuracao)

    # Generate available component variables for the template
    # This logic is used to display hints for template variables in the frontend
    available_component_variables = []
    if template:
        for tc in template.componentes.all(): # Iterate through TemplateComponente
            component_name_in_template = tc.componente.nome.lower().replace(' ', '_') # Example: "Fechadura" -> "fechadura"
            
            # Try to get the actual ConfiguracaoComponenteEscolha for this template component
            try:
                cce = configuracao.componentes_escolha.get(template_componente=tc)
                actual_description = cce.descricao_personalizada or f'(Nenhuma descrição personalizada. Será o nome do componente real: {cce.componente_real.nome})'
            except ConfiguracaoComponenteEscolha.DoesNotExist:
                actual_description = _('(Nenhuma escolha de componente feita ainda para este template de componente)')

            available_component_variables.append({
                'name': f'componentes.{component_name_in_template}',
                'description': actual_description
            })
            
    context = {
        'form': form,
        'formset': formset,
        'template': template, # Pass template to context for template rendering
        'initial_component_choices_data': json.dumps(initial_component_choices_data), # Pass serialized initial data
        'available_component_variables': available_component_variables,
    }
    return render(request, 'produtos/editar_produto_configuracao.html', context)


def excluir_produto_configuracao(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Handles the deletion of a product configuration.

    On GET, it shows a confirmation page. On POST, it deletes the object.

    Args:
        request: The HttpRequest object.
        pk: The primary key of the ProdutoConfiguracao to delete.

    Returns:
        An HttpResponse object, rendering the confirmation page or
        redirecting to the list upon successful deletion.
    """
    configuracao = get_object_or_404(ProdutoConfiguracao, pk=pk)
    if request.method == 'POST':
        configuracao.delete()
        messages.success(request, _("Configuração de Produto excluída com sucesso!"))
        return redirect('listar_produto_configuracoes')
    context = {'configuracao': configuracao}
    return render(request, 'produtos/confirmar_exclusao_configuracao.html', context)


# =============================================================================
# API Views (for AJAX calls)
# =============================================================================

def get_templates_by_categoria(request: HttpRequest, categoria_id: int) -> JsonResponse:
    """
    API endpoint to return a list of ProdutoTemplates in JSON for a given Categoria.

    Args:
        request: The HttpRequest object.
        categoria_id: The primary key of the Categoria.

    Returns:
        A JsonResponse containing a list of templates (id, nome).
    """
    templates = ProdutoTemplate.objects.filter(categoria_id=categoria_id).values('id', 'nome')
    return JsonResponse(list(templates), safe=False)


def get_atributos_by_template(request: HttpRequest, template_id: int) -> JsonResponse:
    """
    API endpoint to return a list of TemplateAtributo data in JSON for a given ProdutoTemplate.

    Args:
        request: The HttpRequest object.
        template_id: The primary key of the ProdutoTemplate.

    Returns:
        A JsonResponse containing a list of template attributes (id, atributo__id, etc.).
    """
    template = get_object_or_404(ProdutoTemplate, pk=template_id)
    # Return TemplateAtributo data, including the Atributo details
    atributos = template.atributos.all().values(
        'id', # TemplateAtributo ID
        'atributo__id',
        'atributo__nome',
        'atributo__tipo',
        'obrigatorio',
        'ordem'
    )
    return JsonResponse(list(atributos), safe=False)


def get_template_components_by_template(request: HttpRequest, template_id: int) -> JsonResponse:
    """
    API endpoint to return a list of TemplateComponente data in JSON for a given ProdutoTemplate.

    Args:
        request: The HttpRequest object.
        template_id: The primary key of the ProdutoTemplate.

    Returns:
        A JsonResponse containing a list of template components (id, componente__nome, etc.).
    """
    template = get_object_or_404(ProdutoTemplate, pk=template_id)
    template_components = template.componentes.all().values(
        'id',
        'componente__nome',
        'componente__id',
        'quantidade_fixa',
        'atributo_relacionado__atributo__nome',
        'formula_calculo'
    )
    return JsonResponse(list(template_components), safe=False)


def get_all_components(request: HttpRequest) -> JsonResponse:
    """
    API endpoint to return a list of all Componente objects in JSON.

    Args:
        request: The HttpRequest object.

    Returns:
        A JsonResponse containing a list of components (id, nome).
    """
    components = Componente.objects.all().values('id', 'nome')
    return JsonResponse(list(components), safe=False)


def get_components_by_configuration(request: HttpRequest, configuracao_id: int) -> JsonResponse:
    """
    API endpoint to return a list of ConfiguracaoComponente data in JSON for a given ProdutoConfiguracao.

    Args:
        request: The HttpRequest object.
        configuracao_id: The primary key of the ProdutoConfiguracao.

    Returns:
        A JsonResponse containing a list of configuration components (id, componente__id, etc.).
    """
    configuracao = get_object_or_404(ProdutoConfiguracao, pk=configuracao_id)
    components = configuracao.componentes_configuracao.all().values(
        'id',
        'componente__id',
        'componente__nome',
        'componente__unidade',
        'componente__custo_unitario',
        'quantidade',
        'opcional'
    )
    return JsonResponse(list(components), safe=False)