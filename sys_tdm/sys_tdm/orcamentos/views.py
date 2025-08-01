from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q # Import Q for complex queries
from .models import Orcamento, ItemOrcamento
from .forms import OrcamentoForm, CriarOrcamentoForm
from produtos.models import ProdutoInstancia, ProdutoTemplate, Categoria, Atributo, ProdutoConfiguracao, InstanciaAtributo, InstanciaComponente, TemplateAtributo
import re
from datetime import datetime
from .excel_utils import (
    exportar_orcamento_excel as export_excel_util,
    exportar_ficha_producao_excel as export_ficha_producao_util,
    render_instancia_descricao,
)
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import math # Importar o módulo math
import sys # Adicionado para depuração


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
    itens_orcamento = orcamento.itens.all().select_related(
        'configuracao__template__categoria', 
        'instancia__configuracao__template__categoria'
    ).prefetch_related('instancia__atributos__template_atributo__atributo')

    # --- Lógica de Agrupamento e Geração de Código Hierárquico ---
    grouped_items = {}
    for item in itens_orcamento:
        if item.instancia and item.instancia.configuracao:
            config = item.instancia.configuracao
            categoria_nome = config.template.categoria.nome
            if categoria_nome not in grouped_items:
                grouped_items[categoria_nome] = {}
            if config.id not in grouped_items[categoria_nome]:
                grouped_items[categoria_nome][config.id] = []
            grouped_items[categoria_nome][config.id].append(item)

    category_counter = 0
    for categoria_nome, configs in grouped_items.items():
        category_counter += 1
        config_counter = 0
        for config_id, instances in configs.items():
            config_counter += 1
            instance_counter = 0
            for item in instances:
                instance_counter += 1
                item.codigo_hierarquico = f"{category_counter}.{config_counter}.{instance_counter}"

    # --- Fim da Lógica de Geração de Código ---

    total_geral_orcamento = sum(item.total for item in itens_orcamento)

    # Anexa a descrição renderizada para cada item
    for item in itens_orcamento:
        if not hasattr(item, 'codigo_hierarquico'): # Garante que itens sem grupo tenham um código
            item.codigo_hierarquico = "-"
        if item.instancia:
            item.descricao_renderizada = render_instancia_descricao(item)
        elif item.configuracao:
            item.descricao_renderizada = item.configuracao.nome
        else:
            item.descricao_renderizada = item.codigo_item_manual or "Item genérico"

    todas_categorias = Categoria.objects.all()

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        
        form_data = request.POST
        if request.content_type == 'application/json':
            try:
                form_data = json.loads(request.body)
            except json.JSONDecodeError:
                message = "Erro: Requisição JSON inválida."
                messages.error(request, message)
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': message}, status=400)
                else:
                    return redirect('editar_orcamento', orcamento_id=orcamento.id)

        if 'update_orcamento' in form_data:
            orcamento_form = OrcamentoForm(request.POST, instance=orcamento)
            if orcamento_form.is_valid():
                orcamento_form.save()
                messages.success(request, "Orçamento atualizado com sucesso!")
            else:
                messages.error(request, "Erro ao atualizar o orçamento.")
            return redirect('editar_orcamento', orcamento_id=orcamento.id)

        elif 'add_item' in form_data:
            try:
                configuracao_id = form_data.get('configuracao')
                quantidade = int(form_data.get('quantidade', 1))
                preco_unitario = float(form_data.get('preco_unitario') or '0')
                margem_negocio = float(form_data.get('margem_negocio', 0))

                if not configuracao_id:
                    messages.error(request, "Erro: Nenhuma configuração de produto selecionada.")
                    if is_ajax:
                        return JsonResponse({'status': 'error', 'message': "Erro: Nenhuma configuração de produto selecionada."}, status=400)
                    return redirect('editar_orcamento', orcamento_id=orcamento.id)

                configuracao = get_object_or_404(ProdutoConfiguracao, pk=configuracao_id)

                nova_instancia = ProdutoInstancia.objects.create(
                    configuracao=configuracao,
                    codigo=f"{configuracao.nome}-{orcamento.id}-{itens_orcamento.count() + 1}",
                    quantidade=1
                )

                for template_atributo in configuracao.template.atributos.all():
                    valor = form_data.get(f'atributo_{template_atributo.id}')
                    if valor is not None and valor != '':
                        if template_atributo.atributo.tipo == 'num':
                            try:
                                InstanciaAtributo.objects.create(
                                    instancia=nova_instancia,
                                    template_atributo=template_atributo,
                                    valor_num=float(valor)
                                )
                            except ValueError:
                                messages.error(request, f"Valor inválido para o atributo numérico {template_atributo.atributo.nome}: {valor}")
                                if is_ajax:
                                    return JsonResponse({'status': 'error', 'message': f"Valor inválido para o atributo numérico {template_atributo.atributo.nome}: {valor}"}, status=400)
                                return redirect('editar_orcamento', orcamento_id=orcamento.id)
                        else:
                            InstanciaAtributo.objects.create(
                                instancia=nova_instancia,
                                template_atributo=template_atributo,
                                valor_texto=valor
                            )

                atributos_instancia_context = {}
                for ia in nova_instancia.atributos.all():
                    attr_name_for_formula = ia.template_atributo.atributo.nome.lower().replace(' ', '_')
                    if ia.template_atributo.atributo.tipo == 'num' and ia.valor_num is not None:
                        atributos_instancia_context[attr_name_for_formula] = float(ia.valor_num)
                    elif ia.template_atributo.atributo.tipo == 'str' and ia.valor_texto:
                        try:
                            atributos_instancia_context[attr_name_for_formula] = float(ia.valor_texto)
                        except ValueError:
                            atributos_instancia_context[attr_name_for_formula] = ia.valor_texto

                for tc in configuracao.template.componentes.all():
                    quantidade_componente = 0.0
                    
                    if tc.formula_calculo:
                        try:
                            context = {
                                "__builtins__": None,
                                'math': math,
                                'folhas': atributos_instancia_context.get('folhas', 0),
                            }
                            context.update(atributos_instancia_context)

                            if tc.atributo_relacionado:
                                nome_atributo_relacionado = tc.atributo_relacionado.atributo.nome.lower().replace(' ', '_')
                                context['valor_atributo'] = atributos_instancia_context.get(nome_atributo_relacionado, 0)

                            resultado_formula = eval(tc.formula_calculo, context)
                            quantidade_componente = float(resultado_formula)
                        except Exception as e:
                            messages.warning(request, f"Erro ao avaliar a fórmula do componente {tc.componente.nome}: {e}. Usando 0 como quantidade. Fórmula: {tc.formula_calculo}")
                            quantidade_componente = 0.0
                    
                    if tc.quantidade_fixa is not None:
                        quantidade_componente += float(tc.quantidade_fixa)
                    
                    quantidade_componente *= (1 + float(tc.fator_perda))

                    componente_real_escolhido = configuracao.componentes_escolha.filter(template_componente=tc).first()
                    if componente_real_escolhido:
                        InstanciaComponente.objects.create(
                            instancia=nova_instancia,
                            componente=componente_real_escolhido.componente_real,
                            quantidade=quantidade_componente,
                            custo_unitario=componente_real_escolhido.componente_real.custo_unitario,
                            descricao_detalhada=componente_real_escolhido.descricao_personalizada # Add this line
                        )
                    else:
                        messages.warning(request, f"Componente real não encontrado para {tc.componente.nome} na configuração {configuracao.nome}.")

                novo_item_orcamento = ItemOrcamento.objects.create(
                    orcamento=orcamento,
                    instancia=nova_instancia,
                    quantidade=quantidade,
                    preco_unitario=preco_unitario,
                    margem_negocio=margem_negocio
                )

                messages.success(request, "Item adicionado com sucesso!")
                if is_ajax:
                    return JsonResponse({'status': 'success', 'message': 'Item adicionado com sucesso!', 'item_id': novo_item_orcamento.id})
                else:
                    return redirect('editar_orcamento', orcamento_id=orcamento.id)

            except Exception as e:
                message = f"Erro inesperado ao adicionar item: {e}"
                messages.error(request, message)
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': message}, status=400)
                else:
                    return redirect('editar_orcamento', orcamento_id=orcamento.id)

    orcamento_form = OrcamentoForm(instance=orcamento)

    context = {
        'orcamento': orcamento,
        'orcamento_form': orcamento_form,
        'itens_orcamento': itens_orcamento,
        'todas_categorias': todas_categorias,
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

    return redirect('editar_orcamento', orcamento_id=orcamento.id)



@login_required
def exportar_orcamento_excel(request, orcamento_id):
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    itens_orcamento = orcamento.itens.all().select_related('configuracao__template', 'instancia__configuracao__template').prefetch_related('instancia__atributos__template_atributo__atributo')
    
    total_geral_orcamento = 0
    for item in itens_orcamento:
        total_geral_orcamento += item.total

    try:
        # A função export_excel_util precisa ser adaptada para a nova estrutura de itens
        # Por enquanto, passamos os itens brutos. A lógica de agrupamento será refeita no excel_utils
        return export_excel_util(request, orcamento_id, itens_orcamento, total_geral_orcamento)
    except FileNotFoundError:
        messages.error(request, "O arquivo de template Excel (modelo.xlsx) não foi encontrado. Certifique-se de que está em sys_tdm/sys_tdm/static/excel_templates/.")
        return redirect('editar_orcamento', orcamento_id=orcamento.id)
    except Exception as e:
        messages.error(request, f"Erro ao exportar orçamento para Excel: {e}")
        return redirect('editar_orcamento', orcamento_id=orcamento.id)


@login_required
def exportar_ficha_producao(request, orcamento_id):
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    itens_orcamento = orcamento.itens.all().select_related('configuracao__template', 'instancia__configuracao__template').prefetch_related('instancia__atributos__template_atributo__atributo', 'instancia__componentes__componente')

    try:
        return export_ficha_producao_util(request, orcamento, itens_orcamento)
    except FileNotFoundError:
        messages.error(request, "O arquivo de template Excel para a ficha de produção não foi encontrado.")
        return redirect('editar_orcamento', orcamento_id=orcamento.id)
    except Exception as e:
        messages.error(request, f"Erro ao exportar a ficha de produção: {e}")
        return redirect('editar_orcamento', orcamento_id=orcamento.id)





import sys # Adicionado para depuração


@login_required
def gerar_ficha_producao(request, orcamento_id):
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    itens_orcamento = orcamento.itens.all().select_related('configuracao__template', 'instancia__configuracao__template').prefetch_related('instancia__atributos__template_atributo__atributo', 'instancia__componentes__componente')

    try:
        return export_ficha_producao_util(request, orcamento, itens_orcamento)
    except FileNotFoundError:
        messages.error(request, "O arquivo de template Excel para a ficha de produção não foi encontrado.")
        return redirect('editar_orcamento', orcamento_id=orcamento.id)
    except Exception as e:
        messages.error(request, f"Erro ao exportar a ficha de produção: {e}")
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
        r'_V\d+',
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
        # Se o item original tem uma instância, clona a configuração e a instância
        if item_original.instancia:
            instancia_original = item_original.instancia
            configuracao_original = instancia_original.configuracao

            # Clona a ProdutoConfiguracao
            nova_configuracao = ProdutoConfiguracao.objects.create(
                template=configuracao_original.template,
                nome=configuracao_original.nome
            )

            # Clona as escolhas de componentes da configuração
            for escolha_original in configuracao_original.componentes_escolha.all():
                ConfiguracaoComponenteEscolha.objects.create(
                    configuracao=nova_configuracao,
                    template_componente=escolha_original.template_componente,
                    componente_real=escolha_original.componente_real
                )

            # Clona a ProdutoInstancia
            nova_instancia = ProdutoInstancia.objects.create(
                configuracao=nova_configuracao,
                codigo=f"{nova_configuracao.nome}-{novo_orcamento.id}-{item_original.id}",
                quantidade=instancia_original.quantidade
            )

            # Clona os atributos da instância
            for atributo_instancia_original in instancia_original.atributos.all():
                InstanciaAtributo.objects.create(
                    instancia=nova_instancia,
                    template_atributo=atributo_instancia_original.template_atributo,
                    valor_texto=atributo_instancia_original.valor_texto,
                    valor_num=atributo_instancia_original.valor_num
                )

            # Clona os componentes calculados da instância
            for componente_instancia_original in instancia_original.componentes.all():
                InstanciaComponente.objects.create(
                    instancia=nova_instancia,
                    componente=componente_instancia_original.componente,
                    quantidade=componente_instancia_original.quantidade,
                    custo_unitario=componente_instancia_original.custo_unitario,
                    descricao_detalhada=componente_instancia_original.descricao_detalhada
                )

            # Cria o novo ItemOrcamento com a nova instância
            ItemOrcamento.objects.create(
                orcamento=novo_orcamento,
                instancia=nova_instancia,
                quantidade=item_original.quantidade,
                preco_unitario=item_original.preco_unitario,
                codigo_item_manual=item_original.codigo_item_manual
            )
        # Se o item original é uma configuração diretamente (item pai)
        elif item_original.configuracao:
            configuracao_original = item_original.configuracao

            # Clona a ProdutoConfiguracao
            nova_configuracao = ProdutoConfiguracao.objects.create(
                template=configuracao_original.template,
                nome=configuracao_original.nome
            )

            # Clona as escolhas de componentes da configuração
            for escolha_original in configuracao_original.componentes_escolha.all():
                ConfiguracaoComponenteEscolha.objects.create(
                    configuracao=nova_configuracao,
                    template_componente=escolha_original.template_componente,
                    componente_real=escolha_original.componente_real
                )
            
            # Cria o novo ItemOrcamento com a nova configuração (como item pai)
            ItemOrcamento.objects.create(
                orcamento=novo_orcamento,
                configuracao=nova_configuracao,
                quantidade=item_original.quantidade,
                preco_unitario=item_original.preco_unitario,
                codigo_item_manual=item_original.codigo_item_manual
            )
        # Se o item original não tem instância nem configuração (caso genérico)
        else:
            ItemOrcamento.objects.create(
                orcamento=novo_orcamento,
                quantidade=item_original.quantidade,
                preco_unitario=item_original.preco_item_manual
            )

    messages.success(request, f"Nova versão (V{nova_versao_num}) do orçamento criada com sucesso.")
    return redirect('editar_orcamento', orcamento_id=novo_orcamento.id)

@login_required
def get_item_components(request, item_id):
    item_orcamento = get_object_or_404(ItemOrcamento, pk=item_id)
    
    componentes_data = []
    if item_orcamento.instancia:
        for ic in item_orcamento.instancia.componentes.all():
            componentes_data.append({
                'id': ic.id,
                'nome_componente': ic.componente.nome,
                'quantidade': str(ic.quantidade), # Converter para string para JSON
                'custo_unitario': str(ic.custo_unitario), # Converter para string para JSON
                'descricao_detalhada': ic.descricao_detalhada if ic.descricao_detalhada else '',
                'unidade_componente': ic.componente.unidade,
            })
    return JsonResponse(componentes_data, safe=False)

@login_required
def get_item_total_component_cost(request, item_id):
    item_orcamento = get_object_or_404(ItemOrcamento, pk=item_id)
    total_cost = 0.0
    if item_orcamento.instancia:
        for ic in item_orcamento.instancia.componentes.all():
            total_cost += float(ic.quantidade) * float(ic.custo_unitario)
    return JsonResponse({'total_cost': total_cost}, safe=False)

@login_required
def get_templates_for_categoria(request, categoria_id):
    """
    Retorna uma lista de ProdutoTemplates em JSON para uma dada Categoria.
    """
    templates = ProdutoTemplate.objects.filter(categoria_id=categoria_id).order_by('nome')
    data = list(templates.values('id', 'nome'))
    return JsonResponse(data, safe=False)

@login_required
def get_configuracoes_for_template(request, template_id):
    """
    Retorna uma lista de ProdutoConfiguracaos em JSON para um dado ProdutoTemplate.
    """
    configuracoes = ProdutoConfiguracao.objects.filter(template_id=template_id).order_by('nome')
    data = list(configuracoes.values('id', 'nome'))
    return JsonResponse(data, safe=False)

@login_required
def get_atributos_for_configuracao(request, configuracao_id):
    """
    Retorna uma lista de atributos em JSON para uma dada ProdutoConfiguracao.
    """
    configuracao = get_object_or_404(ProdutoConfiguracao, pk=configuracao_id)
    atributos_data = []
    for template_atributo in configuracao.template.atributos.all():
        atributos_data.append({
            'id': template_atributo.id,
            'nome': template_atributo.atributo.nome,
            'tipo': template_atributo.atributo.tipo,
        })
    return JsonResponse(atributos_data, safe=False)

@login_required
@csrf_exempt # Temporarily for testing, should use proper CSRF handling in production
def update_component(request, componente_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            quantidade = data.get('quantidade')
            descricao_detalhada = data.get('descricao_detalhada')
            custo_unitario = data.get('custo_unitario')

            instancia_componente = get_object_or_404(InstanciaComponente, pk=componente_id)
            
            if quantidade is not None:
                instancia_componente.quantidade = float(quantidade)
            if descricao_detalhada is not None:
                instancia_componente.descricao_detalhada = descricao_detalhada
            if custo_unitario is not None:
                instancia_componente.custo_unitario = float(custo_unitario)
            
            instancia_componente.save()

            # Recalcular o custo total dos componentes do item pai
            item_orcamento = instancia_componente.instancia.itemorcamento_set.first() # Assuming one-to-one or one-to-many where we want the first
            total_item_components_cost = 0.0
            if item_orcamento and item_orcamento.instancia:
                for ic in item_orcamento.instancia.componentes.all():
                    total_item_components_cost += float(ic.quantidade) * float(ic.custo_unitario)
                
                # Recalcular preco_unitario do ItemOrcamento
                preco_unitario_recalculado = total_item_components_cost
                if item_orcamento.margem_negocio > 0:
                    preco_unitario_recalculado = total_item_components_cost / (1 - (float(item_orcamento.margem_negocio) / 100))
                
                item_orcamento.preco_unitario = preco_unitario_recalculado
                item_orcamento.save()

            return JsonResponse({'status': 'success', 'message': 'Componente atualizado com sucesso.', 'total_item_components_cost': total_item_components_cost})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
        except InstanciaComponente.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Componente não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método não permitido.'}, status=405)

@login_required
@csrf_exempt
def update_item_components_and_attributes(request, item_id):
    if request.method == 'POST':
        try:
            item = get_object_or_404(ItemOrcamento, pk=item_id)
            data = json.loads(request.body)

            # Atualizar Atributos da Instância
            if 'atributos' in data and item.instancia:
                for attr_data in data['atributos']:
                    instancia_atributo_id = attr_data.get('id')
                    valor = attr_data.get('valor')
                    
                    instancia_atributo = get_object_or_404(InstanciaAtributo, pk=instancia_atributo_id, instancia=item.instancia)
                    
                    if instancia_atributo.template_atributo.atributo.tipo == 'num':
                        instancia_atributo.valor_num = float(valor) if valor is not None and valor != '' else None
                        instancia_atributo.valor_texto = '' # Definir como string vazia para não violar NOT NULL
                    else:
                        instancia_atributo.valor_texto = valor
                        instancia_atributo.valor_num = None
                    instancia_atributo.save()

            # Atualizar Quantidades de Componentes
            if 'componentes' in data and item.instancia:
                for comp_data in data['componentes']:
                    instancia_componente_id = comp_data.get('id')
                    quantidade = comp_data.get('quantidade')

                    instancia_componente = get_object_or_404(InstanciaComponente, pk=instancia_componente_id, instancia=item.instancia)
                    instancia_componente.quantidade = float(quantidade) if quantidade is not None and quantidade != '' else 0.0
                    instancia_componente.save()

            # Recalcular custo de fabrico e preço unitário do item
            total_item_components_cost = 0.0
            if item.instancia:
                for ic in item.instancia.componentes.all():
                    total_item_components_cost += float(ic.quantidade) * float(ic.custo_unitario)
            
            preco_unitario_recalculado = total_item_components_cost
            if item.margem_negocio > 0:
                preco_unitario_recalculado = total_item_components_cost / (1 - (float(item.margem_negocio) / 100))
            
            item.preco_unitario = preco_unitario_recalculado
            item.save()

            return JsonResponse({'status': 'success', 'message': 'Detalhes do item atualizados com sucesso!', 'novo_preco': item.preco_unitario, 'novo_total': item.total})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método não permitido.'}, status=405)

@login_required
def get_item_details(request, item_id):
    item = get_object_or_404(ItemOrcamento, pk=item_id)
    
    total_componentes = 0
    if item.instancia:
        for ic in item.instancia.componentes.all():
            total_componentes += ic.quantidade * ic.custo_unitario

    data = {
        'id': item.id,
        'quantidade': item.quantidade,
        'preco_unitario': float(item.preco_unitario),
        'total': float(item.total),
        'margem_negocio': float(item.margem_negocio) if item.margem_negocio is not None else 0,
        'total_componentes': float(total_componentes),
        'instancia_atributos': []
    }

    if item.instancia:
        for ia in item.instancia.atributos.all():
            data['instancia_atributos'].append({
                'id': ia.id,
                'nome': ia.template_atributo.atributo.nome,
                'tipo': ia.template_atributo.atributo.tipo,
                'valor_texto': ia.valor_texto,
                'valor_num': float(ia.valor_num) if ia.valor_num is not None else None,
            })

    return JsonResponse(data)

@login_required
def get_item_row_html(request, item_id):
    item = get_object_or_404(ItemOrcamento, pk=item_id)
    # Anexa a descrição renderizada para ser usada no template _item_row.html
    if item.instancia:
        item.descricao_renderizada = render_instancia_descricao(item)
    elif item.configuracao:
        item.descricao_renderizada = item.configuracao.nome
    else:
        item.descricao_renderizada = item.codigo_item_manual or "Item genérico"
    return render(request, 'orcamentos/_item_row.html', {'item': item})

@login_required
@csrf_exempt
def update_item_details(request, item_id):
    if request.method == 'POST':
        try:
            item = get_object_or_404(ItemOrcamento, pk=item_id)
            data = json.loads(request.body)

            preco_unitario = data.get('preco_unitario')
            margem_negocio = data.get('margem_negocio')

            if preco_unitario is not None:
                item.preco_unitario = float(preco_unitario)
            
            if margem_negocio is not None:
                item.margem_negocio = float(margem_negocio)
            
            item.save()

            return JsonResponse({
                'status': 'success', 
                'message': 'Item atualizado com sucesso.',
                'novo_preco': item.preco_unitario,
                'novo_total': item.total
            })
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
        except ItemOrcamento.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Item não encontrado.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método não permitido.'}, status=405)