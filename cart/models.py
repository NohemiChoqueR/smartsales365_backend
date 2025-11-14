# cart/models.py
from django.db import models
from django.core.exceptions import ValidationError

class Cart(models.Model):
    empresa = models.ForeignKey('tenants.Empresa', on_delete=models.CASCADE, null=True, blank=True)
    usuario = models.ForeignKey('users.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    estado = models.CharField(max_length=20, choices=[
        ('activo', 'Activo'),
        ('confirmado', 'Confirmado'),
        ('cancelado', 'Cancelado'),
        ('inactivo', 'Inactivo'),
    ], default='activo')

    class Meta:
        db_table = 'cart'
    
    def __str__(self):
        # SOLUCIÓN: Usar string para evitar errores de importación
        try:
            email = self.usuario.email
        except:
            email = "sin email"
        return f"Carrito #{self.id} - {email} - {self.estado}"

    @classmethod
    def get_or_create_active(cls, usuario, empresa=None):
        cart = cls.objects.filter(usuario=usuario, estado='activo').first()
        if cart:
            return cart, False
        cart = cls.objects.create(usuario=usuario, empresa=empresa)
        return cart, True
    
    @property
    def total(self):
        """Calcula el total del carrito automáticamente"""
        try:
            return sum(item.subtotal for item in self.item.all())
        except:
            return 0
    
    @property
    def cantidad_items(self):
        """Cantidad total de productos en el carrito"""
        try:
            return sum(item.cantidad for item in self.item.all())
        except:
            return 0


class CartItem(models.Model):
    empresa = models.ForeignKey('tenants.Empresa', on_delete=models.CASCADE, null=True, blank=True)
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)  # Cambié 'item' a 'items'
    producto = models.ForeignKey('products.Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'cart_item'
    
    def __str__(self):
        try:
            nombre = self.producto.nombre
        except:
            nombre = "producto no disponible"
        return f"Item #{self.id} - {nombre} - {self.cantidad}"

    def save(self, *args, **kwargs):
        if self.cart and not self.empresa:
            self.empresa = self.cart.empresa
        
        # SOLUCIÓN: Manejar el caso cuando producto no existe o no tiene precio_venta
        if (not self.precio_unitario or float(self.precio_unitario) == 0):
            try:
                if hasattr(self.producto, 'precio_venta') and self.producto.precio_venta is not None:
                    self.precio_unitario = self.producto.precio_venta
            except:
                # Si hay algún error, mantener el precio_unitario actual o usar un default
                if not self.precio_unitario:
                    self.precio_unitario = 0
        
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        """Precio total para este item (cantidad × precio)"""
        try:
            return self.cantidad * self.precio_unitario
        except:
            return 0