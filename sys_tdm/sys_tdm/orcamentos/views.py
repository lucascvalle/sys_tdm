"""
Views for the Orcamentos (Budgets) application.

This module handles the creation, editing, listing, versioning, and exporting
of budgets and their items. It contains significant business logic for
instantiating products and calculating their components based on configurations.
"""

from __future__ import annotations
import json
import math
import re
from datetime import datetime
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext_lazy as _

from produtos.models import (
    Categoria, Atributo, ProdutoTemplate, ProdutoInstancia, ProdutoConfiguracao,
    InstanciaAtributo, InstanciaComponente, TemplateAtributo, TemplateComponente,
    ConfiguracaoComponenteEscolha, Componente
)
from .models import Orcamento, ItemOrcamento
from .forms import OrcamentoForm, CriarOrcamentoForm
from .excel_utils import (
    exportar_orcamento_excel as export_excel_util,
    exportar_ficha_producao_excel as export_ficha_producao_util,
    render_instancia_descricao,
)


# =============================================================================
# HTML Rendering Views
# =============================================================================

@login_required
def listar_orcamentos(request: HttpRequest) -> HttpResponse:
    """
    Lists all budgets with optional search functionality.

    Args:
        request: The HttpRequest object. Supports GET parameter 'q' for search.

    Returns:
        An HttpResponse object rendering the list of budgets.
    """
    orcamentos = Orcamento.objects.all().order_by('-criado_em')

    query = request.GET.get('q')
    if query:
        orcamentos = orcamentos.filter(
            Q(codigo_legado__icontains=query) |
            Q(nome_cliente__icontains=query) |
            Q(codigo_cliente__icontains=query) |
            Q(codigo_agente__icontains=query)
        ).distinct()

    context = {'orcamentos': orcamentos, 'query': query}
    return render(request, 'orcamentos/listar_orcamentos.html', context)


@login_required
def criar_orcamento(request: HttpRequest) -> HttpResponse:
    """
    Handles the creation of a new budget.

    On GET, it displays an empty form. On POST, it validates the form data
    and creates a new Orcamento object, extracting details from the legacy code.

    Args:
        request: The HttpRequest object.

    Returns:
        An HttpResponse object, either rendering the form or redirecting
        to the budget list upon successful creation.
    """
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
                        messages.error(request, _("Um orçamento com o código '{codigo}' e versão {versao} já existe.").format(codigo=codigo_legado, versao=versao))
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
                    messages.success(request, _("Orçamento '{codigo}' criado com sucesso!").format(codigo=orcamento.codigo_legado))
                    return redirect('listar_orcamentos')

                except ValueError as e:
                    messages.error(request, _("Erro ao parsear dados do código: {error}").format(error=e))
                except Exception as e:
                    messages.error(request, _("Ocorreu um erro inesperado: {error}").format(error=e))
            else:
                messages.error(request, _("Formato do código legado inválido. Use o formato: EP107-250625.80-ELLA_V2"))
        else:
            # Se o formulário não for válido (ex: campo vazio), renderiza com erros
            messages.error(request, _("Por favor, corrija os erros no formulário."))
    else:
        form = CriarOrcamentoForm()
    context = {'form': form}
    return render(request, 'orcamentos/criar_orcamento.html', context)


@login_required
def editar_orcamento(request: HttpRequest, orcamento_id: int) -> HttpResponse:
    """
    Handles the editing of a budget and its items.

    This view manages:
    - Displaying budget details and its items.
    - Updating budget details (e.g., client name).
    - Adding new product instances as items to the budget via AJAX.

    Args:
        request: The HttpRequest object.
        orcamento_id: The primary key of the Orcamento to edit.

    Returns:
        An HttpResponse object rendering the budget edit page.
    """
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    itens_orcamento = orcamento.itens.all().select_related(
        'configuracao__template__categoria',
        'instancia__configuracao__template__categoria'
    ).prefetch_related('instancia__atributos__template_atributo__atributo')

    # --- Lógica de Agrupamento e Geração de Código Hierárquico ---
    # This logic groups items by category and configuration to generate a hierarchical code
    # for display purposes, typically in reports or detailed views.
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
            # Calls a utility function to render a detailed description for the instance
            item.descricao_renderizada = render_instancia_descricao(item)
        elif item.configuracao:
            item.descricao_renderizada = item.configuracao.nome
        else:
            item.descricao_renderizada = item.codigo_item_manual or _("Item genérico")

    todas_categorias = Categoria.objects.all()

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        
        form_data = request.POST
        if request.content_type == 'application/json':
            try:
                form_data = json.loads(request.body)
            except json.JSONDecodeError:
                message = _("Erro: Requisição JSON inválida.")
                messages.error(request, message)
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': message}, status=400)
                else:
                    return redirect('editar_orcamento', orcamento_id=orcamento.id)

        if 'update_orcamento' in form_data:
            orcamento_form = OrcamentoForm(request.POST, instance=orcamento)
            if orcamento_form.is_valid():
                orcamento_form.save()
                messages.success(request, _("Orçamento atualizado com sucesso!"))
            else:
                messages.error(request, _("Erro ao atualizar o orçamento."))
            return redirect('editar_orcamento', orcamento_id=orcamento.id)

        elif 'add_item' in form_data:
            try:
                configuracao_id = form_data.get('configuracao')
                quantidade = int(form_data.get('quantidade', 1))
                preco_unitario = float(form_data.get('preco_unitario') or '0')
                margem_negocio = float(form_data.get('margem_negocio', 0))

                if not configuracao_id:
                    messages.error(request, _("Erro: Nenhuma configuração de produto selecionada."))
                    if is_ajax:
                        return JsonResponse({'status': 'error', 'message': _("Erro: Nenhuma configuração de produto selecionada.")}, status=400)
                    return redirect('editar_orcamento', orcamento_id=orcamento.id)

                configuracao = get_object_or_404(ProdutoConfiguracao, pk=configuracao_id)

                # Create a new ProdutoInstancia
                nova_instancia = ProdutoInstancia.objects.create(
                    configuracao=configuracao,
                    codigo=f"{configuracao.nome}-{orcamento.id}-{itens_orcamento.count() + 1}",
                    quantidade=1 # Quantity for the instance itself, not the budget item quantity
                )

                # Process instance attributes
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
                                messages.error(request, _("Valor inválido para o atributo numérico {nome}: {valor}").format(nome=template_atributo.atributo.nome, valor=valor))
                                if is_ajax:
                                    return JsonResponse({'status': 'error', 'message': _("Valor inválido para o atributo numérico {nome}: {valor}").format(nome=template_atributo.atributo.nome, valor=valor)}, status=400)
                                return redirect('editar_orcamento', orcamento_id=orcamento.id)
                        else:
                            InstanciaAtributo.objects.create(
                                instancia=nova_instancia,
                                template_atributo=template_atributo,
                                valor_texto=valor
                            )

                # Prepare context for formula evaluation (if formulas are used)
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

                # Process instance components based on template components and formulas
                for tc in configuracao.template.componentes.all():
                    quantidade_componente = 0.0
                    
                    if tc.formula_calculo: # Evaluate formula if present
                        try:
                            # Define a safe execution environment for eval()
                            # Only allow 'math' module and specific variables
                            context = {
                                "__builtins__": None, # Restrict built-ins
                                'math': math,
                                'folhas': atributos_instancia_context.get('folhas', 0), # Example variable
                            }
                            context.update(atributos_instancia_context)

                            if tc.atributo_relacionado:
                                nome_atributo_relacionado = tc.atributo_relacionado.atributo.nome.lower().replace(' ', '_')
                                context['valor_atributo'] = atributos_instancia_context.get(nome_atributo_relacionado, 0)

                            # WARNING: Using eval() is a security risk if formulas come from untrusted sources.
                            # Consider a safer expression evaluator for production environments.
                            resultado_formula = eval(tc.formula_calculo, {"__builtins__": None}, context)
                            quantidade_componente = float(resultado_formula)
                        except Exception as e:
                            messages.warning(request, _("Erro ao avaliar a fórmula do componente {nome}: {error}. Usando 0 como quantidade. Fórmula: {formula}").format(nome=tc.componente.nome, error=e, formula=tc.formula_calculo))
                            quantidade_componente = 0.0
                    
                    if tc.quantidade_fixa is not None: # Add fixed quantity if present
                        quantidade_componente += float(tc.quantidade_fixa)
                    
                    # Apply loss factor
                    quantidade_componente *= (1 + float(tc.fator_perda))

                    # Find the actual component chosen for this configuration
                    componente_real_escolhido = configuracao.componentes_escolha.filter(template_componente=tc).first()
                    if componente_real_escolhido:
                        InstanciaComponente.objects.create(
                            instancia=nova_instancia,
                            componente=componente_real_escolhido.componente_real,
                            quantidade=quantidade_componente,
                            custo_unitario=componente_real_escolhido.componente_real.custo_unitario,
                            descricao_detalhada=componente_real_escolhido.descricao_personalizada
                        )
                    else:
                        messages.warning(request, _("Componente real não encontrado para {nome} na configuração {configuracao_nome}.").format(nome=tc.componente.nome, configuracao_nome=configuracao.nome))

                # Create the new ItemOrcamento linked to the created instance
                novo_item_orcamento = ItemOrcamento.objects.create(
                    orcamento=orcamento,
                    instancia=nova_instancia,
                    quantidade=quantidade,
                    preco_unitario=preco_unitario,
                    margem_negocio=margem_negocio
                )

                messages.success(request, _("Item adicionado com sucesso!"))
                if is_ajax:
                    return JsonResponse({'status': 'success', 'message': _('Item adicionado com sucesso!'), 'item_id': novo_item_orcamento.id})
                else:
                    return redirect('editar_orcamento', orcamento_id=orcamento.id)

            except Exception as e:
                message = _("Erro inesperado ao adicionar item: {error}").format(error=e)
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
        'todas_categorias': Categoria.objects.all(),
        'total_geral_orcamento': total_geral_orcamento,
    }
    return render(request, 'orcamentos/editar_orcamento.html', context)


@login_required
def remover_item_orcamento(request: HttpRequest, orcamento_id: int, item_id: int) -> HttpResponse:
    """
    Handles the removal of an item from a budget.

    Args:
        request: The HttpRequest object.
        orcamento_id: The primary key of the Orcamento.
        item_id: The primary key of the ItemOrcamento to remove.

    Returns:
        A redirect to the budget edit page.
    """
    if request.method == 'POST':
        orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
        item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
        item.delete()
        messages.success(request, _("Item removido com sucesso!"))
    return redirect('editar_orcamento', orcamento_id=orcamento_id)


@login_required
def atualizar_item_orcamento(request: HttpRequest, orcamento_id: int, item_id: int) -> HttpResponse:
    """
    Handles the update of an item's quantity or unit price within a budget.

    Args:
        request: The HttpRequest object.
        orcamento_id: The primary key of the Orcamento.
        item_id: The primary key of the ItemOrcamento to update.

    Returns:
        A redirect to the budget edit page.
    """
    if request.method == 'POST':
        orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
        item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
        
        try:
            if 'quantidade' in request.POST:
                quantidade = int(request.POST.get('quantidade'))
                if quantidade <= 0:
                    messages.error(request, _("A quantidade deve ser um número positivo."))
                else:
                    item.quantidade = quantidade
                    item.save()
                    messages.success(request, _("Quantidade atualizada com sucesso!"))
            
            if 'preco_unitario' in request.POST:
                preco_unitario = float(request.POST.get('preco_unitario'))
                if preco_unitario < 0:
                    messages.error(request, _("O preço unitário não pode ser negativo."))
                else:
                    item.preco_unitario = preco_unitario
                    item.save()
                    messages.success(request, _("Preço unitário atualizado com sucesso!"))

        except ValueError:
            messages.error(request, _("Valor inválido para quantidade ou preço unitário."))
        except Exception as e:
            messages.error(request, _("Erro ao atualizar item: {error}").format(error=e))

    return redirect('editar_orcamento', orcamento_id=orcamento.id)


@login_required
def exportar_orcamento_excel(request: HttpRequest, orcamento_id: int) -> HttpResponse:
    """
    Exports the budget data to an Excel file.

    Args:
        request: The HttpRequest object.
        orcamento_id: The ID of the Orcamento to export.

    Returns:
        An HttpResponse with the Excel file attachment or a redirect on error.
    """
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    itens_orcamento = orcamento.itens.all().select_related(
        'configuracao__template', 'instancia__configuracao__template'
    ).prefetch_related('instancia__atributos__template_atributo__atributo')
    
    total_geral_orcamento = 0
    for item in itens_orcamento:
        total_geral_orcamento += item.total

    try:
        # The export_excel_util function needs to be adapted for the new item structure.
        # For now, we pass raw items. Grouping logic will be redone in excel_utils.
        return export_excel_util(request, orcamento_id, itens_orcamento, total_geral_orcamento)
    except FileNotFoundError:
        messages.error(request, _("O arquivo de template Excel (modelo.xlsx) não foi encontrado. Certifique-se de que está em sys_tdm/sys_tdm/static/excel_templates/."))
        return redirect('editar_orcamento', orcamento_id=orcamento_id)
    except Exception as e:
        messages.error(request, _("Erro ao exportar orçamento para Excel: {error}").format(error=e))
        return redirect('editar_orcamento', orcamento_id=orcamento_id)


@login_required
def exportar_ficha_producao(request: HttpRequest, orcamento_id: int) -> HttpResponse:
    """
    Exports the production sheet for a budget to an Excel file.

    Args:
        request: The HttpRequest object.
        orcamento_id: The ID of the Orcamento for the production sheet.

    Returns:
        An HttpResponse with the Excel file or a redirect on error.
    """
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    itens_orcamento = orcamento.itens.all().select_related(
        'configuracao__template', 'instancia__configuracao__template'
    ).prefetch_related('instancia__atributos__template_atributo__atributo', 'instancia__componentes__componente')

    try:
        return export_ficha_producao_util(request, orcamento, itens_orcamento)
    except FileNotFoundError:
        messages.error(request, _("O arquivo de template Excel para a ficha de produção não foi encontrado."))
        return redirect('editar_orcamento', orcamento_id=orcamento_id)
    except Exception as e:
        messages.error(request, _("Erro ao exportar a ficha de produção: {error}").format(error=e))
        return redirect('editar_orcamento', orcamento_id=orcamento_id)


@login_required
def gerar_ficha_producao(request: HttpRequest, orcamento_id: int) -> HttpResponse:
    """
    Generates the production sheet for a budget.

    This view is likely a wrapper around `exportar_ficha_producao`.

    Args:
        request: The HttpRequest object.
        orcamento_id: The primary key of the Orcamento.

    Returns:
        An HttpResponse with the Excel file or a redirect on error.
    """
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    itens_orcamento = orcamento.itens.all().select_related(
        'configuracao__template', 'instancia__configuracao__template'
    ).prefetch_related('instancia__atributos__template_atributo__atributo', 'instancia__componentes__componente')

    try:
        return export_ficha_producao_util(request, orcamento, itens_orcamento)
    except FileNotFoundError:
        messages.error(request, _("O arquivo de template Excel para a ficha de produção não foi encontrado."))
        return redirect('editar_orcamento', orcamento_id=orcamento_id)
    except Exception as e:
        messages.error(request, _("Erro ao exportar a ficha de produção: {error}").format(error=e))
        return redirect('editar_orcamento', orcamento_id=orcamento_id)


@login_required
def excluir_orcamento(request: HttpRequest, orcamento_id: int) -> HttpResponse:
    """
    Handles the deletion of a budget.

    On POST, it deletes the budget. On GET, it redirects with an error message.

    Args:
        request: The HttpRequest object.
        orcamento_id: The primary key of the Orcamento to delete.

    Returns:
        A redirect to the budget list.
    """
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    if request.method == 'POST':
        orcamento.delete()
        messages.success(request, _("Orçamento '{codigo}' excluído com sucesso!").format(codigo=orcamento.codigo_legado))
        return redirect('listar_orcamentos')
    # Por simplicidade, vamos redirecionar para a lista com uma mensagem de erro se não for POST
    messages.error(request, _("Método não permitido para exclusão direta."))
    return redirect('listar_orcamentos')


@login_required
def versionar_orcamento(request: HttpRequest, orcamento_id: int) -> HttpResponse:
    """
    Creates a new version of an existing budget, cloning all its items
    and their associated product instances.

    Args:
        request: The HttpRequest object.
        orcamento_id: The primary key of the Orcamento to version.

    Returns:
        A redirect to the edit page of the newly created budget version.
    """
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

    messages.success(request, _("Nova versão (V{versao}) do orçamento criada com sucesso.").format(versao=nova_versao_num))
    return redirect('editar_orcamento', orcamento_id=novo_orcamento.id)


@login_required
def get_item_components(request: HttpRequest, item_id: int) -> JsonResponse:
    """
    API endpoint to return components data for a given ItemOrcamento.

    Args:
        request: The HttpRequest object.
        item_id: The primary key of the ItemOrcamento.

    Returns:
        A JsonResponse containing a list of component details.
    """
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
def get_item_total_component_cost(request: HttpRequest, item_id: int) -> JsonResponse:
    """
    API endpoint to return the total cost of components for a given ItemOrcamento.

    Args:
        request: The HttpRequest object.
        item_id: The primary key of the ItemOrcamento.

    Returns:
        A JsonResponse containing the total cost.
    """
    item_orcamento = get_object_or_404(ItemOrcamento, pk=item_id)
    total_cost = 0.0
    if item_orcamento.instancia:
        for ic in item_orcamento.instancia.componentes.all():
            total_cost += float(ic.quantidade) * float(ic.custo_unitario)
    return JsonResponse({'total_cost': total_cost}, safe=False)


@login_required
def get_templates_for_categoria(request: HttpRequest, categoria_id: int) -> JsonResponse:
    """
    API endpoint to return a list of ProdutoTemplates in JSON for a given Categoria.

    Args:
        request: The HttpRequest object.
        categoria_id: The primary key of the Categoria.

    Returns:
        A JsonResponse containing a list of templates (id, nome).
    """
    templates = ProdutoTemplate.objects.filter(categoria_id=categoria_id).order_by('nome')
    data = list(templates.values('id', 'nome'))
    return JsonResponse(data, safe=False)


@login_required
def get_configuracoes_for_template(request: HttpRequest, template_id: int) -> JsonResponse:
    """
    API endpoint to return a list of ProdutoConfiguracaos in JSON for a given ProdutoTemplate.

    Args:
        request: The HttpRequest object.
        template_id: The primary key of the ProdutoTemplate.

    Returns:
        A JsonResponse containing a list of configurations (id, nome).
    """
    configuracoes = ProdutoConfiguracao.objects.filter(template_id=template_id).order_by('nome')
    data = list(configuracoes.values('id', 'nome'))
    return JsonResponse(data, safe=False)


@login_required
def get_atributos_for_configuracao(request: HttpRequest, configuracao_id: int) -> JsonResponse:
    """
    API endpoint to return a list of attributes in JSON for a given ProdutoConfiguracao.

    Args:
        request: The HttpRequest object.
        configuracao_id: The primary key of the ProdutoConfiguracao.

    Returns:
        A JsonResponse containing a list of attributes (id, nome, tipo).
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
def update_component(request: HttpRequest, componente_id: int) -> JsonResponse:
    """
    API endpoint to update a specific `InstanciaComponente`.

    Args:
        request: The HttpRequest object, expecting a JSON body with update data.
        componente_id: The primary key of the InstanciaComponente to update.

    Returns:
        A JsonResponse with the status of the operation.
    """
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

            return JsonResponse({'status': 'success', 'message': _('Componente atualizado com sucesso.'), 'total_item_components_cost': total_item_components_cost})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': _('Invalid JSON.')}, status=400)
        except InstanciaComponente.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': _('Componente não encontrado.')}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': _('Método não permitido.')}, status=405)


@login_required
@csrf_exempt
def update_item_components_and_attributes(request: HttpRequest, item_id: int) -> JsonResponse:
    """
    API endpoint to update the components and attributes of an `ItemOrcamento`'s instance.

    Args:
        request: The HttpRequest object, expecting a JSON body with update data.
        item_id: The primary key of the ItemOrcamento to update.

    Returns:
        A JsonResponse with the status of the operation.
    """
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

            return JsonResponse({'status': 'success', 'message': _('Detalhes do item atualizados com sucesso!'), 'novo_preco': item.preco_unitario, 'novo_total': item.total})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': _('Invalid JSON.')}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': _('Método não permitido.')}, status=405)


@login_required
def get_item_details(request: HttpRequest, item_id: int) -> JsonResponse:
    """
    API endpoint to return detailed information about a single budget item.

    Args:
        request: The HttpRequest object.
        item_id: The primary key of the ItemOrcamento.

    Returns:
        A JsonResponse containing the item's details.
    """
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
def get_item_row_html(request: HttpRequest, item_id: int) -> HttpResponse:
    """
    API endpoint to render and return the HTML for a single budget item row.

    Args:
        request: The HttpRequest object.
        item_id: The primary key of the ItemOrcamento.

    Returns:
        An HttpResponse rendering the item row.
    """
    item = get_object_or_404(ItemOrcamento, pk=item_id)
    # Anexa a descrição renderizada para ser usada no template _item_row.html
    if item.instancia:
        item.descricao_renderizada = render_instancia_descricao(item)
    elif item.configuracao:
        item.descricao_renderizada = item.configuracao.nome
    else:
        item.descricao_renderizada = item.codigo_item_manual or _("Item genérico")
    return render(request, 'orcamentos/_item_row.html', {'item': item})


@login_required
@csrf_exempt
def update_item_details(request: HttpRequest, item_id: int) -> JsonResponse:
    """
    API endpoint to update the details of a budget item (e.g., quantity,
    margin) and its underlying components and attributes.

    Args:
        request: The HttpRequest object, expecting a JSON body.
        item_id: The primary key of the ItemOrcamento to update.

    Returns:
        A JsonResponse with the status of the operation.
    """
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
                'message': _('Item atualizado com sucesso.'),
                'novo_preco': item.preco_unitario,
                'novo_total': item.total
            })
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': _('Invalid JSON.')}, status=400)
        except ItemOrcamento.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': _('Item não encontrado.')}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': _('Método não permitido.')}, status=405)
