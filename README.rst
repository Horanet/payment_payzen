———————————————————————————————————————————————
===============================================

Description
-----------

Ce module permet le paiement des factures et bons de commande via l'intermédiaire de paiement Payzen.
Ce module surcharge le modèle payment.transaction pour y ajouter la relation avec le modèle account.voucher.

Détail
^^^^^^^
Lors d'un paiement, un objet de transaction est généré. Les factures et bons de commande correspondant y sont rattachés.

Lorsqu'une transaction réussie, le statut des factures et bons de commandes associés change pour valiuder la procédure de paiment.



Crédits
-------

Contributors
^^^^^^^^^^^^

* Adrien Didenot <adrien.didenot@horanet.com>
* Alexandre Papin <alexandre.papin@horanet.com>

Maintainer
^^^^^^^^^^

.. image:: http://www.horanet.com/img/logo_oemhoranet.jpg
   :alt: Horanet
   :target: http://www.horanet.com/

This module is maintained by Horanet.