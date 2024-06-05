from django.db.models.signals import pre_save
from django.dispatch import receiver

from CORE.models import OrderBuyToken


@receiver(pre_save, sender=OrderBuyToken)
def comission_signal(sender, **kwargs):
    """
    Считаем комиссию партнера

    :param sender:
    :param kwargs:
    :return:
    """
    try:
        old_order = OrderBuyToken.objects.get(id=sender.id)
        if sender.state == OrderBuyToken.STATE_WITHDRAWN and old_order.state != OrderBuyToken.STATE_WITHDRAWN:
            if sender.widget:
                sender.widget.partner.balance += sender.p2p_quantity * sender.widget.partner_commission
                sender.widget.partner.save()
    except:
        pass