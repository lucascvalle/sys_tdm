from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q # Import Q for complex queries
from .models import Orcamento, ItemOrcamento
from .forms import OrcamentoForm
from produtos.models import ProdutoInstancia, ProdutoTemplate, Categoria, Atributo, InstanciaAtributo
import re
from datetime import datetime
from .excel_utils import exportar_orcamento_excel as export_excel_util

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

def criar_orcamento(request):
    if request.method == 'POST':
        codigo_legado = request.POST.get('codigo_legado', '').strip()
        if not codigo_legado:
            messages.error(request, "O código legado não pode estar vazio.")
            return render(request, 'orcamentos/criar_orcamento.html', {})

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
                    return render(request, 'orcamentos/criar_orcamento.html', {})

                from django.contrib.auth import get_user_model
                User = get_user_model()
                usuario_padrao = User.objects.first()

                orcamento = Orcamento.objects.create(
                    codigo_legado=codigo_legado,
                    usuario=usuario_padrao,
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

    return render(request, 'orcamentos/criar_orcamento.html', {})

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

def remover_item_orcamento(request, orcamento_id, item_id):
    if request.method == 'POST':
        orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
        item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
        item.delete()
        messages.success(request, "Item removido com sucesso!")
    return redirect('editar_orcamento', orcamento_id=orcamento_id)

def atualizar_item_orcamento(request, orcamento_id, item_id):
    if request.method == 'POST':
        orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
        item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
        
        try:
            quantidade = int(request.POST.get('quantidade'))
            preco_unitario = float(request.POST.get('preco_unitario'))

            if quantidade <= 0:
                messages.error(request, "A quantidade deve ser um número positivo.")
            elif preco_unitario < 0:
                messages.error(request, "O preço unitário não pode ser negativo.")
            else:
                item.quantidade = quantidade
                item.preco_unitario = preco_unitario
                item.save() # Isso recalculará o total devido ao método save no modelo ItemOrcamento
                messages.success(request, "Item atualizado com sucesso!")
        except ValueError:
            messages.error(request, "Quantidade e/ou preço unitário inválidos.")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar item: {e}")

    return redirect('editar_orcamento', orcamento_id=orcamento_id)



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

