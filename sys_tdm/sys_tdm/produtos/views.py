from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q # Import Q for complex queries
from .models import Categoria, Atributo, ItemMaterial, ProdutoTemplate, ProdutoInstancia, InstanciaAtributo
from orcamentos.models import ItemOrcamento, Orcamento
from .forms import CategoriaForm, AtributoForm, ItemMaterialForm, ProdutoTemplateForm, ProdutoInstanciaForm, TemplateAtributoFormSet
from django.http import JsonResponse

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
            Q(descricao__icontains=query) |
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
    instancias = ProdutoInstancia.objects.all()
    # Você pode adicionar lógica de busca aqui se necessário
    return render(request, 'produtos/listar_produto_instancias.html', {'instancias': instancias})


# TODO: Adicionar views para outros modelos (Atributo, ItemMaterial, etc.)
# TODO: Adicionar views para edição, exclusão, e detalhes de cada item.

# --- API Views ---

def get_templates_by_categoria(request, categoria_id):
    templates = ProdutoTemplate.objects.filter(categoria_id=categoria_id).values('id', 'nome')
    return JsonResponse(list(templates), safe=False)

def get_atributos_by_template(request, template_id):
    template = get_object_or_404(ProdutoTemplate, pk=template_id)
    atributos = template.atributos.all().values('atributo__id', 'atributo__nome', 'atributo__tipo')
    return JsonResponse(list(atributos), safe=False)

def get_instancia_detalhes_json(request, instancia_id):
    instancia = get_object_or_404(ProdutoInstancia, pk=instancia_id)

    # Detalhes da Instância
    instancia_data = {
        'id': instancia.id,
        'codigo': instancia.codigo,
        'template_nome': instancia.template.nome,
        'quantidade': instancia.quantidade,
        'atributos': []
    }

    # Atributos da Instância
    for attr_instancia in instancia.atributos.all():
        valor = attr_instancia.valor_num if attr_instancia.atributo.tipo == 'num' else attr_instancia.valor_texto
        instancia_data['atributos'].append({
            'nome': attr_instancia.atributo.nome,
            'valor': str(valor) # Converter para string para JSON
        })

    # Orçamentos relacionados
    orcamentos_data = []
    # Encontrar todos os ItemOrcamento que usam esta ProdutoInstancia
    itens_orcamento = ItemOrcamento.objects.filter(instancia=instancia).select_related('orcamento')

    for item_orcamento in itens_orcamento:
        orcamento = item_orcamento.orcamento
        orcamentos_data.append({
            'id': orcamento.id,
            'codigo_legado': orcamento.codigo_legado,
            'nome_cliente': orcamento.nome_cliente,
            'data_solicitacao': orcamento.data_solicitacao.strftime('%d/%m/%Y') if orcamento.data_solicitacao else None,
            'versao': orcamento.versao,
        })

    return JsonResponse({'instancia': instancia_data, 'orcamentos': orcamentos_data})