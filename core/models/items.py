# core/models/items.py
class DoorItemManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(tipo='PORT')


class DoorItem(Item):
    objects = DoorItemManager()

    class Meta:
        proxy = True

    def calculate_price(self, altura, largura, material):
        area = altura * largura
        return self.preco_base * area * self.material_multiplier(material)