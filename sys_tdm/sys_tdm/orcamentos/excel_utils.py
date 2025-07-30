from django.http import HttpResponse
from django.conf import settings
import openpyxl
import io
from copy import copy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from openpyxl.utils import get_column_letter

# Importações de modelos necessárias
from orcamentos.models import Orcamento, ItemOrcamento
from produtos.models import ProdutoInstancia, ProdutoTemplate, Categoria, Atributo, ProdutoConfiguracao, InstanciaAtributo, InstanciaComponente, Componente, TemplateComponente

def copy_cell(source_cell, target_cell):
    """Copia valor e estilo de forma defensiva, garantindo que number_format nunca seja None."""
    target_cell.value = source_cell.value if source_cell.value is not None else ""
    if source_cell.has_style:
        target_cell.font = copy(source_cell.font)
        target_cell.border = copy(source_cell.border)
        target_cell.fill = copy(source_cell.fill)
        target_cell.protection = copy(source_cell.protection)
        target_cell.alignment = copy(source_cell.alignment)
        target_cell.number_format = source_cell.number_format or 'General'

def copy_style(source_cell, target_cell):
    """Copia apenas o estilo de forma defensiva, garantindo que number_format nunca seja None."""
    if source_cell.has_style:
        target_cell.font = copy(source_cell.font)
        target_cell.border = copy(source_cell.border)
        target_cell.fill = copy(source_cell.fill)
        target_cell.protection = copy(source_cell.protection)
        target_cell.alignment = copy(source_cell.alignment)
        target_cell.number_format = source_cell.number_format or 'General'

def _formatar_detalhes_item_ficha(item):
    display_name = ""
    componentes_str = ""

    if item.instancia:
        configuracao = item.instancia.configuracao
        display_name = configuracao.nome

        # Atributos da Instância
        numeric_attrs = []
        non_numeric_attrs = []
        for attr_instancia in item.instancia.atributos.all():
            if attr_instancia.template_atributo.atributo.tipo == 'num' and attr_instancia.valor_num is not None:
                numeric_attrs.append(str(int(attr_instancia.valor_num)))
            elif attr_instancia.template_atributo.atributo.tipo == 'str' and attr_instancia.valor_texto:
                non_numeric_attrs.append(attr_instancia.valor_texto)
        
        if non_numeric_attrs:
            display_name += f" - {' '.join(non_numeric_attrs)}"
        if numeric_attrs:
            display_name += f" ({'x'.join(numeric_attrs)})mm"

        # Componentes Calculados da Instância
        componentes_str = "\n--- Componentes ---\n"
        for ic in item.instancia.componentes.all():
            componentes_str += f"- {ic.componente.nome}: {ic.quantidade} {ic.componente.unidade} (Custo Unit: {ic.custo_unitario})\n"
            if ic.descricao_detalhada:
                componentes_str += f"  Detalhes: {ic.descricao_detalhada}\n"

    elif item.configuracao:
        display_name = item.configuracao.nome
        # Para itens que são apenas configurações (pais), podemos listar os componentes do template
        # mas sem quantidades calculadas, pois não há uma instância específica.
        componentes_str = "\n--- Componentes (Padrão) ---\n"
        for tc in item.configuracao.template.componentes.all():
            # Tenta encontrar a escolha de componente real para esta configuração
            escolha = item.configuracao.componentes_escolha.filter(template_componente=tc).first()
            componente_nome = escolha.componente_real.nome if escolha else tc.componente.nome
            componentes_str += f"- {componente_nome}: {tc.quantidade_fixa or 'Variável'} {tc.componente.unidade}\n"
    else:
        display_name = "Item de Orçamento Genérico"

    if item.codigo_item_manual:
        display_name = f"{item.codigo_item_manual} - {display_name}"

    return display_name + componentes_str

def exportar_orcamento_excel(request, orcamento_id, itens_orcamento, total_geral_orcamento):
    orcamento = get_object_or_404(Orcamento, pk=orcamento_id)
    template_path = settings.BASE_DIR / 'static' / 'excel_templates' / 'modelo.xlsx'
    clauses_path = settings.BASE_DIR / 'static' / 'excel_templates' / 'modelo_clausulas.xlsx'

    try:
        workbook = openpyxl.load_workbook(template_path)
        sheet = workbook.active
        sheet['B3'] = orcamento.nome_cliente or ''
        sheet['B4'] = f"Obra: {orcamento.codigo_legado or ''}"
        sheet['B5'] = orcamento.codigo_legado or ''

        # Capturar estilos das linhas modelo
        category_model_row_styles = [copy(sheet.cell(row=9, column=col_idx)) for col_idx in range(1, 8)]
        template_model_row_styles = [copy(sheet.cell(row=10, column=col_idx)) for col_idx in range(1, 8)]
        instance_model_row_styles = [copy(sheet.cell(row=11, column=col_idx)) for col_idx in range(1, 8)]

        current_row = 9
        
        # Re-group items for Excel export based on the new hierarchy
        # This logic should ideally be done in the view and passed already grouped
        # For now, a simplified grouping for demonstration
        grouped_items = {}
        for item in itens_orcamento:
            if item.configuracao: # This is a parent item (configuration)
                config_key = (item.configuracao.template.categoria.nome, item.configuracao.nome)
                if config_key not in grouped_items:
                    grouped_items[config_key] = {
                        'parent_item': item,
                        'instances': []
                    }
            elif item.instancia and item.instancia.configuracao: # This is an instance item
                config_key = (item.instancia.configuracao.template.categoria.nome, item.instancia.configuracao.nome)
                if config_key not in grouped_items:
                     # If a config parent doesn't exist, create a dummy one for grouping
                    grouped_items[config_key] = {
                        'parent_item': None, # No explicit parent ItemOrcamento for this config
                        'instances': []
                    }
                grouped_items[config_key]['instances'].append(item)

        category_counter = 0
        for (categoria_nome, config_nome), data in grouped_items.items():
            category_counter += 1
            
            # Write Category/Configuration Header
            sheet.insert_rows(current_row)
            for col_idx in range(1, 8):
                copy_style(category_model_row_styles[col_idx - 1], sheet.cell(row=current_row, column=col_idx))
            sheet.cell(row=current_row, column=1).value = f"{category_counter}"
            sheet.cell(row=current_row, column=2).value = f"{categoria_nome} - {config_nome}"
            current_row += 1

            instance_counter = 0
            for item in data['instances']:
                instance_counter += 1
                sheet.insert_rows(current_row)
                for col_idx in range(1, 8):
                    copy_style(instance_model_row_styles[col_idx - 1], sheet.cell(row=current_row, column=col_idx))
                sheet.cell(row=current_row, column=1).value = f"{category_counter}.{instance_counter}"
                sheet.cell(row=current_row, column=2).value = _formatar_detalhes_item_ficha(item) # Use the updated formatter
                sheet.cell(row=current_row, column=3).value = item.instancia.configuracao.template.unidade or ''
                sheet.cell(row=current_row, column=4).value = item.quantidade
                sheet.cell(row=current_row, column=5).value = float(item.preco_unitario) if item.preco_unitario is not None else 0.0
                sheet.cell(row=current_row, column=6).value = float(item.total) if item.total is not None else 0.0
                current_row += 1

        # Remover as 3 linhas de modelo originais (9, 10, 11) que agora estão abaixo dos dados inseridos
        sheet.delete_rows(current_row, 3)

        clauses_workbook = openpyxl.load_workbook(clauses_path)
        clauses_sheet = clauses_workbook.active
        
        row_offset = current_row - 1
        for r_idx, row in enumerate(clauses_sheet.iter_rows(), 1):
            for c_idx, source_cell in enumerate(row, 1):
                target_cell = sheet.cell(row=r_idx + row_offset, column=c_idx)
                copy_cell(source_cell, target_cell)

        for merged_range in clauses_sheet.merged_cells.ranges:
            min_col_letter = get_column_letter(merged_range.min_col)
            max_col_letter = get_column_letter(merged_range.max_col)
            new_range_string = f"{min_col_letter}{merged_range.min_row + row_offset}:{max_col_letter}{merged_range.max_row + row_offset}"
            sheet.merge_cells(new_range_string)

        sheet.cell(row=current_row, column=7).value = float(total_geral_orcamento) if total_geral_orcamento is not None else 0.0

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)

        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="orcamento_{orcamento.codigo_legado}.xlsx"'
        return response

    except FileNotFoundError as e:
        messages.error(request, f"Ocorreu um erro: O arquivo {e.filename} não foi encontrado. Verifique se os templates 'modelo.xlsx' e 'modelo_clausulas.xlsx' estão no lugar certo.")
        return redirect('editar_orcamento', orcamento_id=orcamento_id)
    except Exception as e:
        messages.error(request, f"Erro ao exportar orçamento para Excel: {e}")
        return redirect('editar_orcamento', orcamento_id=orcamento_id)

def exportar_ficha_producao_excel(request, orcamento, itens_orcamento):
    template_path = settings.BASE_DIR / 'static' / 'excel_templates' / 'modelo_ficha_producao.xlsx'

    try:
        workbook = openpyxl.load_workbook(template_path)
        sheet = workbook.active

        # Preencher informações do cabeçalho
        sheet['B3'] = orcamento.nome_cliente or ''
        sheet['B4'] = f"Obra: {orcamento.codigo_legado or ''}"
        sheet['B5'] = orcamento.codigo_legado or ''

        # Capturar estilos das linhas modelo
        item_model_row_styles = [copy(sheet.cell(row=9, column=col_idx)) for col_idx in range(1, 8)]

        current_row = 9
        item_counter = 0
        for item in itens_orcamento:
            item_counter += 1
            sheet.insert_rows(current_row)
            for col_idx in range(1, 8):
                copy_style(item_model_row_styles[col_idx - 1], sheet.cell(row=current_row, column=col_idx))
            
            # Formatar e inserir os detalhes do item
            detalhes_item = _formatar_detalhes_item_ficha(item)
            cell = sheet.cell(row=current_row, column=2, value=detalhes_item)
            cell.alignment = openpyxl.styles.Alignment(wrap_text=True)

            sheet.cell(row=current_row, column=1).value = f"{item_counter}"
            sheet.cell(row=current_row, column=3).value = item.quantidade
            current_row += 1

        # Remover a linha de modelo original
        sheet.delete_rows(current_row, 1)

        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)

        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="ficha_producao_{orcamento.codigo_legado}.xlsx"'
        return response

    except FileNotFoundError:
        messages.error(request, "O arquivo de template Excel para a ficha de produção (modelo_ficha_producao.xlsx) não foi encontrado.")
        return redirect('editar_orcamento', orcamento_id=orcamento.id)
    except Exception as e:
        messages.error(request, f"Erro ao exportar a ficha de produção: {e}")
        return redirect('editar_orcamento', orcamento_id=orcamento.id)