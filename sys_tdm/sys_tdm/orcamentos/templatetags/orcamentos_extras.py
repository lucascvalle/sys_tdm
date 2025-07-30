from django import template
from produtos.models import InstanciaAtributo

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name='add_class')
def add_class(value, arg):
    return value.as_widget(attrs={'class': arg})

@register.filter(name='format_item_display_name')
def format_item_display_name(item):
    display_name = ""
    if item.instancia:
        configuracao = item.instancia.configuracao
        display_name = configuracao.nome
        
        # Adicionar atributos da instância se existirem
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

    elif item.configuracao:
        display_name = item.configuracao.nome
    
    if item.codigo_item_manual:
        display_name = f"{item.codigo_item_manual} - {display_name}"

    return display_name