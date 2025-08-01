from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q # Import Q for complex queries
from .models import Categoria, Atributo, ProdutoTemplate, ProdutoInstancia, ProdutoConfiguracao, TemplateAtributo, Componente, ConfiguracaoComponenteEscolha, InstanciaAtributo, InstanciaComponente, TemplateComponente
from orcamentos.models import ItemOrcamento, Orcamento
from .forms import CategoriaForm, AtributoForm, ProdutoTemplateForm, ProdutoInstanciaForm, TemplateAtributoFormSet, ProdutoConfiguracaoForm, ConfiguracaoComponenteEscolhaFormSet, InstanciaAtributoFormSet, InstanciaComponenteFormSet
from django.http import JsonResponse
import json

def produtos_home(request):
    return render(request, 'produtos/produtos_home.html')

def listar_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, 'produtos/listar_categorias.html', {'categorias': categorias})

def criar_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria criada com sucesso!")
            return redirect('listar_categorias')
        else:
            messages.error(request, "Erro ao criar categoria. Verifique os dados.")
    else:
        form = CategoriaForm()
    return render(request, 'produtos/criar_categoria.html', {'form': form})

def listar_produtos_template(request):
    produtos_template = ProdutoTemplate.objects.all()
    
    query = request.GET.get('q')
    if query:
        produtos_template = produtos_template.filter(
            Q(nome__icontains=query) |
            Q(categoria__nome__icontains=query)
        ).distinct()

    return render(request, 'produtos/listar_produtos_template.html', {'produtos_template': produtos_template, 'query': query})

def criar_produto_template(request):
    if request.method == 'POST':
        form = ProdutoTemplateForm(request.POST)
        formset = TemplateAtributoFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            produto_template = form.save()
            formset.instance = produto_template
            formset.save()
            messages.success(request, "Template de Produto criado com sucesso!")
            return redirect('listar_produtos_template')
        else:
            messages.error(request, "Erro ao criar Template de Produto. Verifique os dados e os atributos.")
    else:
        form = ProdutoTemplateForm()
        formset = TemplateAtributoFormSet()
    return render(request, 'produtos/criar_produto_template.html', {'form': form, 'formset': formset})

# Views para ProdutoInstancia
def listar_produto_instancias(request):
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

# Views para ProdutoConfiguracao
def listar_produto_configuracoes(request):
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

def criar_produto_configuracao(request):
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

            messages.success(request, "Configuração de Produto criada com sucesso!")
            return redirect('listar_produto_configuracoes')
        else:
            messages.error(request, "Erro ao criar Configuração de Produto. Verifique os dados e as escolhas de componentes.")
    else:
        initial_form_data = {}
        if template:
            initial_form_data['template'] = template.id
        form = ProdutoConfiguracaoForm(initial=initial_form_data)
        formset = ConfiguracaoComponenteEscolhaFormSet()

    context = {
        'form': form,
        'formset': formset,
        'template': template, # Pass template to context for template rendering
    }
    return render(request, 'produtos/criar_produto_configuracao.html', context)

def editar_produto_configuracao(request, pk):
    configuracao = get_object_or_404(ProdutoConfiguracao, pk=pk)
    template = configuracao.template # Get the template from the existing configuration

    # Prepare initial data for ConfiguracaoComponenteEscolhaFormSet
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
            messages.success(request, "Configuração de Produto atualizada com sucesso!")
            return redirect('listar_produto_configuracoes')
        else:
            messages.error(request, "Erro ao atualizar Configuração de Produto. Verifique os dados e as escolhas de componentes.")
    else:
        form = ProdutoConfiguracaoForm(instance=configuracao)
        formset = ConfiguracaoComponenteEscolhaFormSet(instance=configuracao)

    context = {
        'form': form,
        'formset': formset,
        'template': template, # Pass template to context for template rendering
        'initial_component_choices_data': json.dumps(initial_component_choices_data), # Pass serialized initial data
    }
    return render(request, 'produtos/editar_produto_configuracao.html', context)

def excluir_produto_configuracao(request, pk):
    configuracao = get_object_or_404(ProdutoConfiguracao, pk=pk)
    if request.method == 'POST':
        configuracao.delete()
        messages.success(request, "Configuração de Produto excluída com sucesso!")
        return redirect('listar_produto_configuracoes')
    return render(request, 'produtos/confirmar_exclusao_configuracao.html', {'configuracao': configuracao})


# --- API Views ---

def get_templates_by_categoria(request, categoria_id):
    templates = ProdutoTemplate.objects.filter(categoria_id=categoria_id).values('id', 'nome')
    return JsonResponse(list(templates), safe=False)

def get_atributos_by_template(request, template_id):
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

def get_template_components_by_template(request, template_id):
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

def get_all_components(request):
    components = Componente.objects.all().values('id', 'nome')
    return JsonResponse(list(components), safe=False)

def get_components_by_configuration(request, configuracao_id):
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
