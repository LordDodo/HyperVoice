<h1>HyperVoice</h1>
<p>HyperVoice est une application de chat vocal en temps réel permettant aux utilisateurs de se connecter à des salons de discussion et de communiquer via des messages audio.</p>

<h2>Fonctionnalités</h2>
<ul>
<li>Connexion des utilisateurs avec un pseudo unique</li>
        <li>Création et gestion de salons de discussion</li>
        <li>Envoi de messages audio en temps réel</li>
        <li>Utilisation du micro par défaut du système</li>
    </ul>

  <h2>Installation</h2>
    <p>Pour installer et exécuter HyperVoice, suivez les étapes ci-dessous :</p>
    <ol>
        <li>Clonez le dépôt Git :</li>
        <pre><code>git clone &lt;URL_DU_DEPOT&gt;</code></pre>
        <li>Accédez au répertoire du projet :</li>
        <pre><code>cd HyperVoice</code></pre>
        <li>Installez les dépendances requises :</li>
        <pre><code>pip install -r requirements.txt</code></pre>
    </ol>

   <h2>Utilisation</h2>
    <h3>Serveur</h3>
    <p>Pour démarrer le serveur, exécutez la commande suivante :</p>
    <pre><code>python server.py serveur</code></pre>

  <h3>Client</h3>
    <p>Pour démarrer le client, exécutez la commande suivante :</p>
    <pre><code>python client.py</code></pre>
    <p>Lors de la première exécution, vous serez invité à entrer un pseudo.</p>

  <h2>Structure du Projet</h2>
    <ul>
        <li><code>server.py</code> : Contient la logique du serveur, y compris la gestion des connexions et des salons.</li>
        <li><code>client.py</code> : Contient la logique du client, y compris l'interface utilisateur et la gestion des périphériques audio.</li>
        <li><code>requirements.txt</code> : Liste des dépendances Python nécessaires pour exécuter le projet.</li>
    </ul>

  <h2>Contribuer</h2>
    <p>Les contributions sont les bienvenues ! Pour contribuer, veuillez suivre les étapes ci-dessous :</p>
    <ol>
        <li>Fork le dépôt</li>
        <li>Créez une branche pour votre fonctionnalité (<code>git checkout -b feature/ma-fonctionnalite</code>)</li>
        <li>Commitez vos modifications (<code>git commit -am 'Ajout de ma fonctionnalité'</code>)</li>
        <li>Push vers la branche (<code>git push origin feature/ma-fonctionnalite</code>)</li>
        <li>Ouvrez une Pull Request</li>
    </ol>

  <h2>Licence</h2>
    <p>Ce projet est sous licence MIT. Voir le fichier <code>LICENSE</code> pour plus de détails.</p>
