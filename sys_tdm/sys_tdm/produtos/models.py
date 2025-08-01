from django.db import models
from django.contrib.auth import get_user_model
from estoque.models import ItemEstocavel

User = get_user_model()

# Create your models here.
class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome

class Atributo(models.Model):
    TIPO_CHOICES = [
        ('num', 'Numérico'),
        ('str', 'Texto'),
        ('choice', 'Escolha'),
    ]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    def __str__(self):
        return self.nome

class Componente(models.Model):
    nome = models.CharField(max_length=200)
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    unidade = models.CharField(max_length=20)
    itens_compativeis = models.ManyToManyField(ItemEstocavel, blank=True, related_name="componentes_conceptuais")

    def __str__(self):
        return self.nome

class ProdutoTemplate(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='templates')
    nome = models.CharField(max_length=200)
    descricao_instancia_template = models.TextField(
        blank=True, 
        help_text="Template para a descrição da instância individual (ex: para a linha do orçamento). Use variáveis de atributos como {{ altura }}."
    )
    unidade = models.CharField(max_length=50, blank=True, null=True, help_text="Unidade de medida do produto (ex: m², unidade, kg)")

    def __str__(self):
        return f"{self.categoria.nome} - {self.nome}"

class TemplateAtributo(models.Model):
    template = models.ForeignKey(ProdutoTemplate, on_delete=models.CASCADE, related_name='atributos')
    atributo = models.ForeignKey(Atributo, on_delete=models.PROTECT)
    obrigatorio = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0)

    class Meta:
        unique_together = ('template', 'atributo')

    def __str__(self):
        return f"{self.template.nome} - {self.atributo.nome}"

class TemplateComponente(models.Model):
    template = models.ForeignKey(ProdutoTemplate, on_delete=models.CASCADE, related_name='componentes')
    componente = models.ForeignKey(Componente, on_delete=models.PROTECT, default=1)
    quantidade_fixa = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    atributo_relacionado = models.ForeignKey(TemplateAtributo, on_delete=models.PROTECT, null=True, blank=True, related_name='componentes_relacionados')
    formula_calculo = models.TextField(blank=True, help_text="""Fórmula Python para calcular a quantidade do componente. 

**Variáveis disponíveis:**
- `valor_atributo`: O valor do atributo selecionado em 'Atributo Relacionado'.
- Nomes dos atributos da instância (ex: `altura`, `largura`, `numero_de_folhas`). Espaços são substituídos por underscores e letras minúsculas.
- `math`: Módulo Python `math` para funções como `math.ceil()`, `math.floor()`, etc.

**Exemplos:**
- `valor_atributo * 3` (se 'Atributo Relacionado' for 'Número de Folhas')
- `altura / 1000 * 2` (se 'altura' for um atributo da instância)
- `math.ceil(altura / 1200) * numero_de_folhas` (para dobradiças por altura e folhas)
- `10 + (largura / 500)` (quantidade base + variável)

**CUIDADO:** Esta fórmula é avaliada como código Python. Use apenas com fontes confiáveis.
""")
    fator_perda = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ('template', 'componente')

    def __str__(self):
        return f"{self.template.nome} - {self.componente.nome}"

class FormulaTemplate(models.Model):
    template = models.ForeignKey(ProdutoTemplate, on_delete=models.CASCADE, related_name='formulas')
    expressao = models.TextField(
        help_text='Expressão global de cálculo, ex: sum(mat)+sum(mod)*1.2+overhead')

# --- Novos Modelos para a Nova Arquitetura ---

class ProdutoConfiguracao(models.Model):
    template = models.ForeignKey(ProdutoTemplate, on_delete=models.PROTECT, related_name='configuracoes')
    nome = models.CharField(max_length=255, help_text="Ex: Acabamento Fosco, Dobradiças Standard")
    descricao_configuracao_template = models.TextField(
        blank=True,
        help_text="Template para a descrição da configuração (ex: para o agrupador no orçamento). Use variáveis de componentes como {{ componentes.fechadura }}."
    )
    
    def __str__(self):
        return f"{self.template.nome} - {self.nome}"

    def get_detailed_description(self):
        description_parts = [f"Configuração: {self.nome}"]
        if self.componentes_escolha.exists():
            description_parts.append("Componentes:")
            for escolha in self.componentes_escolha.all():
                component_display_name = escolha.descricao_personalizada or escolha.componente_real.nome
                description_parts.append(f"  - {escolha.template_componente.componente.nome}: {component_display_name}")
        return "\n".join(description_parts)

class ConfiguracaoComponenteEscolha(models.Model):
    configuracao = models.ForeignKey(ProdutoConfiguracao, on_delete=models.CASCADE, related_name='componentes_escolha')
    template_componente = models.ForeignKey(TemplateComponente, on_delete=models.PROTECT) # Qual regra de componente do template
    componente_real = models.ForeignKey(Componente, on_delete=models.PROTECT) # Qual componente real usar
    descricao_personalizada = models.CharField(max_length=255, blank=True, null=True, help_text="Descrição personalizada para este componente na configuração (ex: 'LAC. RAL 9010', 'REF JNF XPTO')")

    class Meta:
        unique_together = ('configuracao', 'template_componente')

    def __str__(self):
        return f"{self.configuracao.nome} - {self.template_componente.componente.nome} -> {self.componente_real.nome}"

class ConfiguracaoComponente(models.Model):
    configuracao = models.ForeignKey(ProdutoConfiguracao, on_delete=models.CASCADE, related_name='componentes_configuracao')
    componente = models.ForeignKey(Componente, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    opcional = models.BooleanField(default=False)

    class Meta:
        unique_together = ('configuracao', 'componente')

    def __str__(self):
        return f"{self.configuracao.nome} - {self.componente.nome} ({'Opcional' if self.opcional else 'Obrigatório'})"

# Instâncias para orçamentos (agora com atributos e componentes calculados)
class ProdutoInstancia(models.Model):
    configuracao = models.ForeignKey(ProdutoConfiguracao, on_delete=models.PROTECT, related_name='instancias', null=True, blank=True)
    codigo = models.CharField(max_length=50)
    quantidade = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.configuracao.nome} - {self.codigo}"

class InstanciaAtributo(models.Model):
    instancia = models.ForeignKey(ProdutoInstancia, on_delete=models.CASCADE, related_name='atributos')
    template_atributo = models.ForeignKey(TemplateAtributo, on_delete=models.PROTECT)
    valor_texto = models.CharField(max_length=200, blank=True)
    valor_num = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    class Meta:
        unique_together = ('instancia', 'template_atributo')

    def __str__(self):
        return f"{self.instancia.codigo} - {self.template_atributo.atributo.nome}: {self.valor_texto or self.valor_num}"

class InstanciaComponente(models.Model):
    instancia = models.ForeignKey(ProdutoInstancia, on_delete=models.CASCADE, related_name='componentes')
    componente = models.ForeignKey(Componente, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=4)
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descricao_detalhada = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.instancia.codigo} - {self.componente.nome}: {self.quantidade}"