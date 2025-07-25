from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q # Import Q for complex queries
from .models import Orcamento, ItemOrcamento
from .forms import OrcamentoForm, CriarOrcamentoForm
from produtos.models import ProdutoInstancia, ProdutoTemplate, Categoria, Atributo, InstanciaAtributo
import re
from datetime import datetime
from .excel_utils import exportar_orcamento_excel as export_excel_util
from django.contrib.auth.decorators import login_required

def _format_item_display_name(item):
    non_numeric_attrs = []
    numeric_attrs = []
    for atributo_instancia in item.instancia.atributos.all():
        if atributo_instancia.atributo.tipo == 'num' and atributo_instancia.valor_num is not None:
            numeric_attrs.append(str(int(atributo_instancia.valor_num)))
        elif atributo_instancia.atributo.tipo == 'str' and atributo_instancia.valor_texto:
            non_numeric_attrs.append(atributo_instancia.valor_texto)

    parts = []
    if item.codigo_item_manual:
        parts.append(item.codigo_item_manual)
    
    if non_numeric_attrs:
        parts.append(" - ".join(non_numeric_attrs))

    display_name = " - ".join(parts)

    if numeric_attrs:
        display_name += f" ({'x'.join(numeric_attrs)})mm"

    return display_name

@login_required
def listar_orcamentos(request):
    orcamentos = Orcamento.objects.all().order_by('-criado_em')
    
    query = request.GET.get('q')
    if query:
        orcamentos = orcamentos.filter(
            Q(codigo_legado__icontains=query) |
            Q(nome_cliente__icontains=query) |
            Q(codigo_cliente__icontains=query) |
            Q(codigo_agente__icontains=query)
        ).distinct()

    return render(request, 'orcamentos/listar_orcamentos.html', {'orcamentos': orcamentos, 'query': query})

@login_required
def criar_orcamento(request):
    if request.method == 'POST':
        form = CriarOrcamentoForm(request.POST)
        if form.is_valid():
            codigo_legado = form.cleaned_data['codigo_legado']

            padrao = r"^(EP|PC)(\d+)-(\d{6})\.(\d+)-([A-Z]+)_V(\d+)$"
            match = re.match(padrao, codigo_legado)

            if match:
                tipo_cliente_str = match.group(1)
                codigo_cliente_str = match.group(2)
                data_solicitacao_str = match.group(3)
                num_agente_str = match.group(4)
                iniciais_agente_str = match.group(5)
                versao_str = match.group(6)

                try:
                    data_solicitacao = datetime.strptime(data_solicitacao_str, "%d%m%y").date()
                    versao = int(versao_str)

                    nome_cliente = f"Cliente {codigo_cliente_str}"
                    codigo_agente = f"{num_agente_str}-{iniciais_agente_str}"

                    if Orcamento.objects.filter(codigo_legado=codigo_legado, versao=versao).exists():
                        messages.error(request, f"Um orçamento com o código '{codigo_legado}' e versão {versao} já existe.")
                        return render(request, 'orcamentos/criar_orcamento.html', {'form': form})

                    orcamento = Orcamento.objects.create(
                        codigo_legado=codigo_legado,
                        usuario=request.user,  # Associa ao usuário logado
                        nome_cliente=nome_cliente,
                        tipo_cliente=tipo_cliente_str,
                        codigo_cliente=codigo_cliente_str,
                        data_solicitacao=data_solicitacao,
                        codigo_agente=codigo_agente,
                        versao=versao,
                        versao_base=versao
                    )
                    messages.success(request, f"Orçamento '{orcamento.codigo_legado}' criado com sucesso!")
                    return redirect('listar_orcamentos')

                except ValueError as e:
                    messages.error(request, f"Erro ao parsear dados do código: {e}")
                except Exception as e:
                    messages.error(request, f"Ocorreu um erro inesperado: {e}")
            else:
                messages.error(request, "Formato do código legado inválido. Use o formato: EP107-250625.80-ELLA_V2")
        else:
            # Se o formulário não for válido (ex: campo vazio), renderiza com erros
            messages.error(request, "Por favor, corrija os erros no formulário.")
    else:
        form = CriarOrcamentoForm()
    return render(request, 'orcamentos/criar_orcamento.html', {'form': form})

@login_required
def editar_orcamento(request, orcamento_id):
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    itens_orcamento = orcamento.itens.all().select_related('instancia__template__categoria').prefetch_related('instancia__atributos__atributo')
    
    itens_agrupados_por_categoria = {}
    total_geral_orcamento = 0

    for item in itens_orcamento:
        item.display_name = _format_item_display_name(item)

        categoria_nome = item.instancia.template.categoria.nome
        template_nome = item.instancia.template.nome

        if categoria_nome not in itens_agrupados_por_categoria:
            itens_agrupados_por_categoria[categoria_nome] = {'templates': {}, 'total_categoria': 0, 'quantidade_categoria': 0}
        
        if template_nome not in itens_agrupados_por_categoria[categoria_nome]['templates']:
            itens_agrupados_por_categoria[categoria_nome]['templates'][template_nome] = {'instancias': [], 'total_template': 0, 'quantidade_template': 0}
            
        itens_agrupados_por_categoria[categoria_nome]['templates'][template_nome]['instancias'].append(item)
        itens_agrupados_por_categoria[categoria_nome]['templates'][template_nome]['total_template'] += item.total
        itens_agrupados_por_categoria[categoria_nome]['templates'][template_nome]['quantidade_template'] += item.quantidade
        
        itens_agrupados_por_categoria[categoria_nome]['total_categoria'] += item.total
        itens_agrupados_por_categoria[categoria_nome]['quantidade_categoria'] += item.quantidade

        total_geral_orcamento += item.total

    categorias = Categoria.objects.all()

    if request.method == 'POST':
        if 'update_orcamento' in request.POST:
            orcamento_form = OrcamentoForm(request.POST, instance=orcamento)
            if orcamento_form.is_valid():
                orcamento_form.save()
                messages.success(request, "Orçamento atualizado com sucesso!")
            else:
                messages.error(request, "Erro ao atualizar o orçamento.")
            return redirect('editar_orcamento', orcamento_id=orcamento.id)

        elif 'add_item' in request.POST:
            try:
                template_id = request.POST.get('template')
                quantidade = int(request.POST.get('quantidade', 1))
                preco_unitario = float(request.POST.get('preco_unitario', 0))

                template = get_object_or_404(ProdutoTemplate, pk=template_id)

                nova_instancia = ProdutoInstancia.objects.create(
                    template=template,
                    codigo=f"{template.nome}-{orcamento.id}-{itens_orcamento.count() + 1}",
                    quantidade=1 # A quantidade da instância do produto é sempre 1, a quantidade do item no orçamento é que varia
                )

                for key, value in request.POST.items():
                    if key.startswith('atributo_'):
                        atributo_id = int(key.split('_')[1])
                        atributo = get_object_or_404(Atributo, pk=atributo_id)
                        
                        instancia_atributo_data = {
                            'instancia': nova_instancia,
                            'atributo': atributo,
                        }
                        if atributo.tipo == 'num':
                            try:
                                instancia_atributo_data['valor_num'] = float(value)
                            except ValueError:
                                messages.error(request, f"Valor inválido para o atributo numérico {atributo.nome}: {value}")
                                return redirect('editar_orcamento', orcamento_id=orcamento.id)
                        else:
                            instancia_atributo_data['valor_texto'] = value
                        
                        InstanciaAtributo.objects.create(**instancia_atributo_data)

                ItemOrcamento.objects.create(
                    orcamento=orcamento,
                    instancia=nova_instancia,
                    quantidade=quantidade,
                    preco_unitario=preco_unitario
                )

                messages.success(request, "Item adicionado com sucesso!")
            except Exception as e:
                messages.error(request, f"Erro ao adicionar item: {e}")
            return redirect('editar_orcamento', orcamento_id=orcamento.id)

    orcamento_form = OrcamentoForm(instance=orcamento)

    context = {
        'orcamento': orcamento,
        'orcamento_form': orcamento_form,
        'itens_agrupados_por_categoria': itens_agrupados_por_categoria, # Passar os itens agrupados
        'categorias': categorias,
        'total_geral_orcamento': total_geral_orcamento,
    }
    return render(request, 'orcamentos/editar_orcamento.html', context)

@login_required
def remover_item_orcamento(request, orcamento_id, item_id):
    if request.method == 'POST':
        orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
        item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
        item.delete()
        messages.success(request, "Item removido com sucesso!")
    return redirect('editar_orcamento', orcamento_id=orcamento_id)

@login_required
def atualizar_item_orcamento(request, orcamento_id, item_id):
    if request.method == 'POST':
        orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
        item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
        
        try:
            if 'quantidade' in request.POST:
                quantidade = int(request.POST.get('quantidade'))
                if quantidade <= 0:
                    messages.error(request, "A quantidade deve ser um número positivo.")
                else:
                    item.quantidade = quantidade
                    item.save()
                    messages.success(request, "Quantidade atualizada com sucesso!")
            
            if 'preco_unitario' in request.POST:
                preco_unitario = float(request.POST.get('preco_unitario'))
                if preco_unitario < 0:
                    messages.error(request, "O preço unitário não pode ser negativo.")
                else:
                    item.preco_unitario = preco_unitario
                    item.save()
                    messages.success(request, "Preço unitário atualizado com sucesso!")

        except ValueError:
            messages.error(request, "Valor inválido para quantidade ou preço unitário.")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar item: {e}")

    return redirect('editar_orcamento', orcamento_id=orcamento_id)



@login_required
def exportar_orcamento_excel(request, orcamento_id):
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)

    # Re-calculate grouped items for export view
    itens_orcamento = orcamento.itens.all().select_related('instancia__template__categoria').prefetch_related('instancia__atributos__atributo')
    
    itens_agrupados_por_categoria = {}
    total_geral_orcamento = 0

    for item in itens_orcamento:
        item.display_name = _format_item_display_name(item)

        categoria_nome = item.instancia.template.categoria.nome
        template_nome = item.instancia.template.nome

        if categoria_nome not in itens_agrupados_por_categoria:
            itens_agrupados_por_categoria[categoria_nome] = {'templates': {}, 'total_categoria': 0, 'quantidade_categoria': 0}
        
        if template_nome not in itens_agrupados_por_categoria[categoria_nome]['templates']:
            itens_agrupados_por_categoria[categoria_nome]['templates'][template_nome] = {'instancias': [], 'total_template': 0, 'quantidade_template': 0}
            
        itens_agrupados_por_categoria[categoria_nome]['templates'][template_nome]['instancias'].append(item)
        itens_agrupados_por_categoria[categoria_nome]['templates'][template_nome]['total_template'] += item.total
        itens_agrupados_por_categoria[categoria_nome]['templates'][template_nome]['quantidade_template'] += item.quantidade
        
        itens_agrupados_por_categoria[categoria_nome]['total_categoria'] += item.total
        itens_agrupados_por_categoria[categoria_nome]['quantidade_categoria'] += item.quantidade

        total_geral_orcamento += item.total

    try:
        return export_excel_util(request, orcamento_id, itens_agrupados_por_categoria, total_geral_orcamento)
    except FileNotFoundError:
        messages.error(request, "O arquivo de template Excel (modelo.xlsx) não foi encontrado. Certifique-se de que está em sys_tdm/sys_tdm/static/excel_templates/.")
        return redirect('editar_orcamento', orcamento_id=orcamento.id)
    except Exception as e:
        messages.error(request, f"Erro ao exportar orçamento para Excel: {e}")
        return redirect('editar_orcamento', orcamento_id=orcamento.id)

@login_required
def excluir_orcamento(request, orcamento_id):
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    if request.method == 'POST':
        orcamento.delete()
        messages.success(request, f"Orçamento '{orcamento.codigo_legado}' excluído com sucesso!")
        return redirect('listar_orcamentos')
    # Se for um GET, você pode renderizar uma página de confirmação ou apenas redirecionar
    # Por simplicidade, vamos redirecionar para a lista com uma mensagem de erro se não for POST
    messages.error(request, "Método não permitido para exclusão direta.")
    return redirect('listar_orcamentos')


@login_required
def versionar_orcamento(request, orcamento_id):
    orcamento_original = get_object_or_404(Orcamento, pk=orcamento_id)
    nova_versao_num = orcamento_original.versao + 1

    # Corrigido o uso do re.sub com sintaxe adequada
    novo_codigo_legado = re.sub(
        r'_V\d+$',
        f'_V{nova_versao_num}',
        orcamento_original.codigo_legado
    )

    # Bloco único de criação do novo orçamento (removida a duplicação)
    novo_orcamento = Orcamento.objects.create(
        codigo_legado=novo_codigo_legado,
        usuario=request.user,
        nome_cliente=orcamento_original.nome_cliente,
        tipo_cliente=orcamento_original.tipo_cliente,
        codigo_cliente=orcamento_original.codigo_cliente,
        data_solicitacao=orcamento_original.data_solicitacao,
        codigo_agente=orcamento_original.codigo_agente,
        versao=nova_versao_num,
        versao_base=orcamento_original.versao_base,
    )

    # Clona os itens do orçamento
    for item_original in orcamento_original.itens.all():
        instancia_original = item_original.instancia

        # Clona a ProdutoInstancia
        nova_instancia = ProdutoInstancia.objects.create(
            template=instancia_original.template,
            codigo=f"{instancia_original.template.nome}-{novo_orcamento.id}-{item_original.id}",
            quantidade=instancia_original.quantidade
        )

        # Clona os atributos da instância
        for atributo_instancia_original in instancia_original.atributos.all():
            InstanciaAtributo.objects.create(
                instancia=nova_instancia,
                atributo=atributo_instancia_original.atributo,
                valor_texto=atributo_instancia_original.valor_texto,
                valor_num=atributo_instancia_original.valor_num
            )

        # Cria o novo ItemOrcamento
        ItemOrcamento.objects.create(
            orcamento=novo_orcamento,
            instancia=nova_instancia,
            quantidade=item_original.quantidade,
            preco_unitario=item_original.preco_unitario,
            codigo_item_manual=item_original.codigo_item_manual
        )

    messages.success(request, f"Nova versão (V{nova_versao_num}) do orçamento criada com sucesso.")
    return redirect('editar_orcamento', orcamento_id=novo_orcamento.id)

