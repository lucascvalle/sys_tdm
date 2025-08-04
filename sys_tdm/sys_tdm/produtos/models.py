"""
Models for the Products application.

This module defines the data structures for managing products, including:
- Categories for product classification.
- Attributes that define product characteristics.
- Components that make up products.
- Product Templates as blueprints for product creation.
- Product Configurations for specific product variations.
- Product Instances representing concrete products.
- Relationships between templates, attributes, components, and instances.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from estoque.models import ItemEstocavel

# Get the User model for ForeignKey relationships
User = get_user_model()

# Type checking for potential circular imports
if TYPE_CHECKING:
    from orcamentos.models import ItemOrcamento


class Categoria(models.Model):
    """
    Represents a category for organizing products.

    Categories help in classifying and filtering products within the system.
    """
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Nome da Categoria"),
        help_text=_("O nome que identifica a categoria de produtos.")
    )
    descricao = models.TextField(
        blank=True,
        verbose_name=_("Descrição"),
        help_text=_("Uma descrição opcional para a categoria.")
    )

    class Meta:
        verbose_name = _("Categoria")
        verbose_name_plural = _("Categorias")
        ordering = ['nome']

    def __str__(self) -> str:
        """Returns the string representation of the category."""
        return self.nome


class Atributo(models.Model):
    """
    Defines a configurable attribute that can be assigned to a product.

    Attributes are characteristics of a product that can vary, such as
    height, width, or color. They have a defined type (numeric, text, or choice).
    """
    TIPO_CHOICES = [
        ('num', _('Numérico')),
        ('str', _('Texto')),
        ('choice', _('Escolha')),
    ]
    nome = models.CharField(
        max_length=100,
        verbose_name=_("Nome do Atributo"),
        help_text=_("Nome do atributo (ex: Altura, Cor).")
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        verbose_name=_("Tipo de Atributo"),
        help_text=_("Define se o valor do atributo é numérico, textual ou uma escolha.")
    )

    class Meta:
        verbose_name = _("Atributo")
        verbose_name_plural = _("Atributos")
        ordering = ['nome']

    def __str__(self) -> str:
        """Returns the string representation of the attribute."""
        return f"{self.nome} ({self.get_tipo_display()})"


class Componente(models.Model):
    """
    Represents a component or material used in the composition of a product.

    Components can be linked to one or more stockable items, representing
    the actual materials that can be used to fulfill this component's role.
    """
    nome = models.CharField(
        max_length=200,
        verbose_name=_("Nome do Componente"),
        help_text=_("Nome descritivo do componente (ex: Puxador, Dobradiça).")
    )
    custo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name=_("Custo Unitário"),
        help_text=_("Custo padrão unitário deste componente.")
    )
    unidade = models.CharField(
        max_length=20,
        verbose_name=_("Unidade de Medida"),
        help_text=_("Unidade de medida para este componente (ex: un, m, m²).")
    )
    itens_compativeis = models.ManyToManyField(
        ItemEstocavel,
        blank=True,
        related_name="componentes_conceptuais",
        verbose_name=_("Itens de Estoque Compatíveis"),
        help_text=_("Itens do estoque que podem ser usados para este componente.")
    )

    class Meta:
        verbose_name = _("Componente")
        verbose_name_plural = _("Componentes")
        ordering = ['nome']

    def __str__(self) -> str:
        """Returns the string representation of the component."""
        return f"{self.nome} ({self.unidade})"


class ProdutoTemplate(models.Model):
    """
    A template for creating products.

    It defines the basic structure of a product, including its category,
    the attributes it can have, and the components it is made of.
    This is the blueprint from which specific product configurations and
    instances are created.
    """
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='templates',
        verbose_name=_("Categoria"),
        help_text=_("Categoria à qual este template de produto pertence.")
    )
    nome = models.CharField(
        max_length=200,
        verbose_name=_("Nome do Template"),
        help_text=_("Nome base para o tipo de produto (ex: 'Armário 2 Portas').")
    )
    descricao_instancia_template = models.TextField(
        blank=True,
        verbose_name=_("Template de Descrição da Instância"),
        help_text=_("Template para a descrição da instância individual (ex: para a linha do orçamento). Use variáveis de atributos como {{ altura }}.")
    )
    unidade = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Unidade de Medida"),
        help_text=_("Unidade de medida do produto (ex: m², unidade, kg).")
    )

    class Meta:
        verbose_name = _("Template de Produto")
        verbose_name_plural = _("Templates de Produto")
        ordering = ['nome']

    def __str__(self) -> str:
        """Returns the string representation of the product template."""
        return f"{self.categoria.nome} - {self.nome}"


class TemplateAtributo(models.Model):
    """
    Defines an attribute associated with a `ProdutoTemplate`.

    This model specifies which attributes a product template can have,
    their order, and if they are mandatory.
    """
    template = models.ForeignKey(
        ProdutoTemplate,
        on_delete=models.CASCADE,
        related_name='atributos',
        verbose_name=_("Template de Produto")
    )
    atributo = models.ForeignKey(
        Atributo,
        on_delete=models.PROTECT,
        verbose_name=_("Atributo")
    )
    obrigatorio = models.BooleanField(
        default=True,
        verbose_name=_("Obrigatório"),
        help_text=_("Indica se este atributo é obrigatório para o template.")
    )
    ordem = models.IntegerField(
        default=0,
        verbose_name=_("Ordem"),
        help_text=_("Ordem de exibição do atributo.")
    )

    class Meta:
        verbose_name = _("Atributo do Template")
        verbose_name_plural = _("Atributos do Template")
        unique_together = ('template', 'atributo')
        ordering = ['ordem']

    def __str__(self) -> str:
        """Returns the string representation of the template attribute."""
        return f"{self.template.nome} - {self.atributo.nome}"


class TemplateComponente(models.Model):
    """
    Defines a component associated with a `ProdutoTemplate`.

    This model specifies which components a product template is made of,
    their fixed quantity, related attributes, calculation formulas, and loss factors.
    """
    template = models.ForeignKey(
        ProdutoTemplate,
        on_delete=models.CASCADE,
        related_name='componentes',
        verbose_name=_("Template de Produto")
    )
    componente = models.ForeignKey(
        Componente,
        on_delete=models.PROTECT,
        default=1,
        verbose_name=_("Componente"),
        help_text=_("O componente genérico associado a este template.")
    )
    quantidade_fixa = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("Quantidade Fixa"),
        help_text=_("Quantidade fixa deste componente, se aplicável.")
    )
    atributo_relacionado = models.ForeignKey(
        TemplateAtributo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='componentes_relacionados',
        verbose_name=_("Atributo Relacionado"),
        help_text=_("Atributo do template que pode influenciar a quantidade deste componente.")
    )
    formula_calculo = models.TextField(
        blank=True,
        verbose_name=_("Fórmula de Cálculo"),
        help_text="""Fórmula Python para calcular a quantidade do componente. 

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
    fator_perda = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("Fator de Perda"),
        help_text=_("Fator de perda percentual para este componente (ex: 0.05 para 5%).")
    )

    class Meta:
        verbose_name = _("Componente do Template")
        verbose_name_plural = _("Componentes do Template")
        unique_together = ('template', 'componente')
        ordering = ['template', 'componente__nome']

    def __str__(self) -> str:
        """Returns the string representation of the template component."""
        return f"{self.template.nome} - {self.componente.nome}"


class FormulaTemplate(models.Model):
    """
    Represents a global formula template for product calculations.

    This model allows defining complex expressions that can be used across
    different product calculations.
    """
    template = models.ForeignKey(
        ProdutoTemplate,
        on_delete=models.CASCADE,
        related_name='formulas',
        verbose_name=_("Template de Produto")
    )
    expressao = models.TextField(
        verbose_name=_("Expressão"),
        help_text=_('Expressão global de cálculo, ex: sum(mat)+sum(mod)*1.2+overhead')
    )

    class Meta:
        verbose_name = _("Fórmula do Template")
        verbose_name_plural = _("Fórmulas do Template")
        ordering = ['template']

    def __str__(self) -> str:
        """Returns the string representation of the formula template."""
        return f"Fórmula para {self.template.nome}"


class ProdutoConfiguracao(models.Model):
    """
    A specific configuration of a ProductTemplate.

    It gives a name to a particular setup of a template, allowing for
    different versions or models of the same base product.
    """
    template = models.ForeignKey(
        ProdutoTemplate,
        on_delete=models.PROTECT,
        related_name='configuracoes',
        verbose_name=_("Template de Produto"),
        help_text=_("O template base para esta configuração.")
    )
    nome = models.CharField(
        max_length=255,
        verbose_name=_("Nome da Configuração"),
        help_text=_("Nome específico para esta variação (ex: 'Acabamento Fosco').")
    )
    descricao_configuracao_template = models.TextField(
        blank=True,
        verbose_name=_("Template de Descrição da Configuração"),
        help_text=_("Template para a descrição da configuração (ex: para o agrupador no orçamento). Use variáveis de componentes como {{ componentes.fechadura }}.")
    )

    class Meta:
        verbose_name = _("Configuração de Produto")
        verbose_name_plural = _("Configurações de Produto")
        unique_together = ('template', 'nome')
        ordering = ['template', 'nome']

    def __str__(self) -> str:
        """Returns the string representation of the product configuration."""
        return f"{self.template.nome} - {self.nome}"

    def get_detailed_description(self) -> str:
        """
        Generates a detailed description of the configuration, including its components.

        Returns:
            A string with the detailed description.
        """
        description_parts = [f"Configuração: {self.nome}"]
        if self.componentes_escolha.exists():
            description_parts.append(_("Componentes:"))
            for escolha in self.componentes_escolha.all():
                component_display_name = escolha.descricao_personalizada or escolha.componente_real.nome
                description_parts.append(f"  - {escolha.template_componente.componente.nome}: {component_display_name}")
        return "\n".join(description_parts)


class ConfiguracaoComponenteEscolha(models.Model):
    """
    Represents a specific choice of material for a component in a configuration.

    For a generic component in a configuration (e.g., "Puxador"), this model
    allows specifying a concrete `ItemEstocavel` (e.g., "Puxador Inox Modelo X").
    """
    configuracao = models.ForeignKey(
        ProdutoConfiguracao,
        on_delete=models.CASCADE,
        related_name='componentes_escolha',
        verbose_name=_("Configuração de Produto")
    )
    template_componente = models.ForeignKey(
        TemplateComponente,
        on_delete=models.PROTECT,
        verbose_name=_("Regra de Componente do Template"),
        help_text=_("Qual regra de componente do template esta escolha se refere.")
    ) # Qual regra de componente do template
    componente_real = models.ForeignKey(
        Componente,
        on_delete=models.PROTECT,
        verbose_name=_("Componente Real"),
        help_text=_("Qual componente real do estoque usar para esta regra.")
    ) # Qual componente real usar
    descricao_personalizada = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Descrição Personalizada"),
        help_text=_("Descrição opcional para esta escolha específica (ex: 'LAC. RAL 9010').")
    )

    class Meta:
        verbose_name = _("Escolha de Componente da Configuração")
        verbose_name_plural = _("Escolhas de Componentes da Configuração")
        unique_together = ('configuracao', 'template_componente')
        ordering = ['configuracao', 'template_componente__componente__nome']

    def __str__(self) -> str:
        """Returns the string representation of the component choice."""
        return f"{self.configuracao.nome} - {self.template_componente.componente.nome} -> {self.componente_real.nome}"


class ConfiguracaoComponente(models.Model):
    """
    Represents a component directly associated with a `ProdutoConfiguracao`.

    This model is used for components that are part of a configuration but
    might not be defined by a `TemplateComponente` rule.
    """
    configuracao = models.ForeignKey(
        ProdutoConfiguracao,
        on_delete=models.CASCADE,
        related_name='componentes_configuracao',
        verbose_name=_("Configuração de Produto")
    )
    componente = models.ForeignKey(
        Componente,
        on_delete=models.PROTECT,
        verbose_name=_("Componente")
    )
    quantidade = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("Quantidade"),
        help_text=_("Quantidade deste componente para a configuração.")
    )
    opcional = models.BooleanField(
        default=False,
        verbose_name=_("Opcional"),
        help_text=_("Indica se este componente é opcional na configuração.")
    )

    class Meta:
        verbose_name = _("Componente da Configuração (Direto)")
        verbose_name_plural = _("Componentes da Configuração (Diretos)")
        unique_together = ('configuracao', 'componente')
        ordering = ['configuracao', 'componente__nome']

    def __str__(self) -> str:
        """Returns the string representation of the configured component."""
        return f"{self.configuracao.nome} - {self.componente.nome} ({'Opcional' if self.opcional else 'Obrigatório'})"


class ProdutoInstancia(models.Model):
    """
    A concrete instance of a product, created from a template and configuration.

    This represents a single, unique item in a budget, with its own set of
    attribute values and component instances.
    """
    configuracao = models.ForeignKey(
        ProdutoConfiguracao,
        on_delete=models.PROTECT,
        related_name='instancias',
        null=True,
        blank=True,
        verbose_name=_("Configuração de Produto")
    )
    codigo = models.CharField(
        max_length=50,
        verbose_name=_("Código da Instância"),
        help_text=_("Código único gerado para esta instância do produto.")
    )
    quantidade = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantidade"),
        help_text=_("Quantidade desta instância do produto.")
    )

    class Meta:
        verbose_name = _("Instância de Produto")
        verbose_name_plural = _("Instâncias de Produto")
        ordering = ['-id']

    def __str__(self) -> str:
        """Returns a string representation of the product instance."""
        return f"{self.configuracao.nome} - {self.codigo}"


class InstanciaAtributo(models.Model):
    """
    Stores the value of an attribute for a specific product instance.

    This model links a `ProdutoInstancia` to an `Atributo` and holds
    its specific value (text or numeric).
    """
    instancia = models.ForeignKey(
        ProdutoInstancia,
        on_delete=models.CASCADE,
        related_name='atributos',
        verbose_name=_("Instância de Produto")
    )
    template_atributo = models.ForeignKey(
        TemplateAtributo,
        on_delete=models.PROTECT,
        verbose_name=_("Atributo do Template"),
        help_text=_("O atributo do template ao qual este valor se refere.")
    )
    valor_texto = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Valor (Texto)"),
        help_text=_("Valor textual do atributo, se aplicável.")
    )
    valor_num = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("Valor (Numérico)"),
        help_text=_("Valor numérico do atributo, se aplicável.")
    )

    class Meta:
        verbose_name = _("Atributo da Instância")
        verbose_name_plural = _("Atributos da Instância")
        unique_together = ('instancia', 'template_atributo')
        ordering = ['instancia', 'template_atributo__atributo__nome']

    def __str__(self) -> str:
        """Returns the string representation of the instance attribute."""
        return f"{self.instancia.codigo} - {self.template_atributo.atributo.nome}: {self.valor_texto or self.valor_num}"


class InstanciaComponente(models.Model):
    """
    Represents a specific component within a product instance.

    This model links a `ProdutoInstancia` to a `Componente` and defines
    the quantity, unit cost, and detailed description for this specific instance.
    """
    instancia = models.ForeignKey(
        ProdutoInstancia,
        on_delete=models.CASCADE,
        related_name='componentes',
        verbose_name=_("Instância de Produto")
    )
    componente = models.ForeignKey(
        Componente,
        on_delete=models.PROTECT,
        verbose_name=_("Componente")
    )
    quantidade = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name=_("Quantidade"),
        help_text=_("Quantidade deste componente para a instância.")
    )
    custo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Custo Unitário"),
        help_text=_("Custo unitário do componente no momento da instanciação.")
    )
    descricao_detalhada = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Descrição Detalhada"),
        help_text=_("Descrição específica para este componente na instância.")
    )

    class Meta:
        verbose_name = _("Componente da Instância")
        verbose_name_plural = _("Componentes da Instância")
        unique_together = ('instancia', 'componente')
        ordering = ['instancia', 'componente__nome']

    def __str__(self) -> str:
        """Returns the string representation of the instance component."""
        return f"{self.instancia.codigo} - {self.componente.nome}: {self.quantidade}"
