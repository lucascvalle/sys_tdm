from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class PostoTrabalho(models.Model):
    """
    Modelo para centralizar as máquinas/postos de trabalho.
    """
    nome = models.CharField(max_length=100, unique=True, help_text="Ex: Serra de Bancada, CNC 1, Bancada de Montagem")
    custo_hora = models.DecimalField(max_digits=10, decimal_places=2, help_text="Custo operacional por hora do posto")

    def __str__(self):
        return self.nome


class FichaConsumoObra(models.Model):
    """
    Representa a ficha completa de uma obra, que é preenchida ao longo de vários dias.
    """
    STATUS_CHOICES = [
        ('planejada', 'Planejada'),
        ('em_andamento', 'Em Andamento'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]

    ref_obra = models.CharField(max_length=100, unique=True, help_text="O código ou nome único da obra")
    data_inicio = models.DateField(help_text="A data de início dos trabalhos na obra")
    previsao_entrega = models.DateField(help_text="A data prevista para a conclusão")
    responsavel = models.ForeignKey(User, on_delete=models.PROTECT, related_name='fichas_consumo')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planejada')

    def __str__(self):
        return f"Ficha {self.ref_obra} ({self.get_status_display()})"


class ItemConsumido(models.Model):
    """
    Representa um único lançamento de consumo de material (matéria-prima ou componente)
    dentro de uma FichaConsumoObra.
    """
    ficha_obra = models.ForeignKey(FichaConsumoObra, on_delete=models.CASCADE, related_name='itens_consumidos')
    data_consumo = models.DateField(help_text="O dia em que o material foi efetivamente consumido")

    componente = models.ForeignKey('produtos.Componente', on_delete=models.PROTECT, related_name='consumos_itens', null=True, blank=True)
    descricao_detalhada = models.CharField(max_length=255, blank=True, null=True, help_text="Ex: HTD-H1000, Cor: Branco")

    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    unidade = models.CharField(max_length=10, help_text="Ex: m, kg, un")

    def __str__(self):
        componente_nome = self.componente.nome if self.componente else "N/A"
        return f"{self.quantidade} {self.unidade} de {componente_nome} em {self.data_consumo}"


class Operador(models.Model):
    """
    Representa um operador da fábrica.
    """
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome


class SessaoTrabalho(models.Model):
    """
    Representa um único registro de uso de uma máquina (Sessão de Trabalho),
    que ocorre em um dia específico.
    """
    posto_trabalho = models.ForeignKey(PostoTrabalho, on_delete=models.PROTECT, related_name='sessoes_trabalho')
    operador = models.ForeignKey(Operador, on_delete=models.PROTECT, related_name='sessoes_trabalho')
    ficha_obra = models.ForeignKey(FichaConsumoObra, on_delete=models.PROTECT, related_name='sessoes_trabalho_relacionadas', null=True, blank=True, help_text="A ficha de consumo de obra à qual esta sessão de trabalho está relacionada")
    operacao = models.TextField(help_text="Descrição da tarefa realizada")
    hora_inicio = models.DateTimeField(help_text="Data e hora de início da tarefa")
    hora_saida = models.DateTimeField(null=True, blank=True, help_text="Data e hora de término da tarefa")

    def __str__(self):
        obra_ref = self.ficha_obra.ref_obra if self.ficha_obra else "N/A"
        return f"Sessão em {self.posto_trabalho} por {self.operador} para obra {obra_ref}"