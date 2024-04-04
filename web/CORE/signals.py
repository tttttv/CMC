from django.db.models.signals import pre_save
from django.dispatch import receiver

from CORE.models import P2POrderBuyToken


@receiver(pre_save, sender=P2POrderBuyToken)
def comission_signal(sender, **kwargs):
    """
    Считаем комиссию партнера

    :param sender:
    :param kwargs:
    :return:
    """
    try:
        old_order = P2POrderBuyToken.objects.get(id=sender.id)
        if sender.state == P2POrderBuyToken.STATE_WITHDRAWN and old_order.state != P2POrderBuyToken.STATE_WITHDRAWN:
            if sender.widget:
                sender.widget.partner.balance += sender.p2p_quantity * sender.widget.partner_commission
                sender.widget.partner.save()
    except:
        pass