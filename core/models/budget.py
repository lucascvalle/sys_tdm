class Budget(models.Model):
    codigo_legado = models.CharField(max_length=50, unique=True, validators=[validate_legacy_code])
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    elaborador = models.ForeignKey(User, on_delete=models.PROTECT)

class BudgetVersion(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='versoes')
    versao = models.PositiveIntegerField(default=1)
    itens = models.ManyToManyField(Item, through='BudgetItem')
    total = models.DecimalField(max_digits=12, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True)

class BudgetItem(models.Model):
    versao = models.ForeignKey(BudgetVersion, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    atributos_personalizados = models.JSONField(blank=True, default=dict)