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
from produtos.models import ProdutoInstancia, ProdutoTemplate, Categoria, Atributo, InstanciaAtributo

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

def exportar_orcamento_excel(request, orcamento_id, itens_agrupados_por_categoria, total_geral_orcamento):
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
        category_counter = 0
        for categoria_nome, categoria_data in itens_agrupados_por_categoria.items():
            category_counter += 1
            sheet.insert_rows(current_row)
            for col_idx in range(1, 8):
                copy_style(category_model_row_styles[col_idx - 1], sheet.cell(row=current_row, column=col_idx))
            sheet.cell(row=current_row, column=1).value = f"{category_counter}"
            sheet.cell(row=current_row, column=2).value = categoria_nome or ''
            current_row += 1

            template_counter = 0
            for template_nome, template_data in categoria_data['templates'].items():
                template_counter += 1
                sheet.insert_rows(current_row)
                for col_idx in range(1, 8):
                    copy_style(template_model_row_styles[col_idx - 1], sheet.cell(row=current_row, column=col_idx))
                sheet.cell(row=current_row, column=1).value = f"{category_counter}.{template_counter}"
                sheet.cell(row=current_row, column=2).value = template_data['instancias'][0].instancia.template.descricao or ''
                current_row += 1

                instance_counter = 0
                for item in template_data['instancias']:
                    instance_counter += 1
                    sheet.insert_rows(current_row)
                    for col_idx in range(1, 8):
                        copy_style(instance_model_row_styles[col_idx - 1], sheet.cell(row=current_row, column=col_idx))
                    sheet.cell(row=current_row, column=1).value = f"{category_counter}.{template_counter}.{instance_counter}"
                    sheet.cell(row=current_row, column=2).value = item.display_name or ''
                    sheet.cell(row=current_row, column=3).value = item.instancia.template.unidade or ''
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
