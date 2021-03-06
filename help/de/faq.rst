F.A.Q.
======

.. topic:: Was ist moneyGuru?

    moneyGuru is a personal finance management and planning tool. With it, you can evaluate your current financial situation so you can make informed (and thus better) financial decisions.

.. topic:: Was macht es besser als andere Finanzverwaltungsanwendungen?

    Anstatt dass Sie mühsam Berichte für Ihre Finanzübersicht konfigurieren müssen (oder sich den richtigen vorkonfigurierten Bericht anpassen), haben Sie bei moneyGuru alle Daten tagesaktuell und direkt im Blickfeld. Des weiteren bietet die Anwendung ein effizientes System zur :doc:`Navigation <basics>` innerhalb sowie zum :doc:`Ändern <editing>` Ihrer Daten. Eine durchdachte Unterstützung von mehreren Währungen sowie ein auf doppelter Buchführung basierendes Transaktionssystem gehören ebenfalls zum Lieferumfang.

.. topic:: Welche Einschränkung habe ich in der Demo Version von moneyGuru?

    None, moneyGuru is `Fairware <http://open.hardcoded.net/about/>`__.

.. topic:: Wie kann ich die Währung eines Betrags festlegen?

    Eine Währung lässt sich festlegen, indem dem Betrag der ISO Code der Währung vor- beziehungsweise nachgestellt wird, Großschreibung ist nicht verpflichtend. Beispiele: "42 EUR" oder "usd 42".

.. topic:: Was bedeuten diese grünen Haken vor den Transaktionen?

    Ein grüner Haken deutet an, dass die Transaktion :doc:`wertgestellt <reconciliation>` ist.

.. topic:: Wie gebe ich am einfachsten einen Eröffnungssaldo für ein Konto ein?

    Erzeugen Sie eine Transaktion mit einem Datum, das vor allen anderen Transaktionen liegt, und lassen Sie das Ursprungskonto einfach leer.

.. topic:: Ich habe ein Fremdwährungskonto über eine QIF Datei importiert, aber die Währung wird falsch angezeigt. Was kann ich tun?

    Dateien im QIF Format enthalten keine Währungsinformation. Somit wird moneyGuru solche Konten immer mit der **Basiswährung** importieren. Um einen korrekten Importvorgang zu erzielen, ändern Sie die Basiswährung des Kontos in den Kontoeinstellungen. Diese Änderung modifiziert keine bestehenden Transaktionen!
    
    Möchten Sie ebenfalls bestehende Transaktionen auf eine andere Währung ändern, so selektieren Sie alle Transaktionen dieses Konto und wählen "Details anzeigen" (&#8984;I). Im folgenden Dialog achten Sie bitte darauf, dass alle Transaktionen aktiviert sind, und geben Sie die korrekte Währung ein. Sobald Sie gespeichert haben, wurden alle Transaktionen auf die andere Währung umgestellt.

.. topic:: Manche Konten werden unter "Eigenkapital" und "Profit & Verlust" grau angezeigt. Warum?

    Grau angezeigte Konten bedeuten, dass diese deaktiviert sind. Deaktivierte Konten werden nicht in die Berechnung der Gesamtsummen einbezogen. Um diese in die Berechnung zu inkludieren, wählen Sie das entsprechende Konto aus und klicken auf |basics_account_in|.

.. topic:: Ich habe eine Frage, die hier noch nicht beantwortet ist. Was kann ich tun?

    There's a `moneyGuru forum`_ which can probably help you. If it's a bug report or feature
    request you have, you should head to `moneyGuru's issue tracker on GitHub`_.

.. _moneyGuru forum: http://forum.hardcoded.net/
.. _moneyGuru's issue tracker on GitHub: https://github.com/hsoft/moneyguru/issues
.. |basics_account_in| image:: image/basics_account_in.png
