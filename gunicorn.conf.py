"""Réglages gunicorn — chargés automatiquement (gunicorn cherche
`gunicorn.conf.py` dans son répertoire de travail courant), sans toucher à
la ligne ExecStart du service systemd (`ExecStart=... gunicorn
config.wsgi:application --bind 0.0.0.0:8001 --workers 3`), qui reste la
source du nombre de workers.

worker_class="gthread" + threads=2 plutôt que le worker sync par défaut :
avec 3 workers sync purs, une requête lente (téléchargement d'un document
volumineux, écriture SQLite en attente d'un verrou) bloque tout le worker
qui la traite — aucune autre requête ne peut y être servie pendant ce
temps. Avec des workers threadés, chaque worker peut traiter plusieurs
requêtes en même temps dès que l'une d'elles attend une E/S (lecture
disque, requête réseau vers l'assistant IA...), sans consommer de mémoire
supplémentaire significative (contrairement à l'ajout de workers
supplémentaires, plus coûteux en RAM sur ce serveur à 11 Go).
"""

worker_class = "gthread"
threads = 2

# Recycle chaque worker après un nombre de requêtes légèrement aléatoire
# (jitter) — évite qu'ils ne redémarrent tous en même temps, ce qui
# créerait un pic de charge synchronisé au moment du recyclage. Protège
# aussi contre une fuite mémoire lente qui s'accumulerait sur la durée.
max_requests = 500
max_requests_jitter = 50

# Une requête qui dépasse ce délai (téléchargement bloqué, verrou SQLite
# jamais libéré...) fait tuer et relancer le worker plutôt que de rester
# bloquée indéfiniment. 60 s plutôt que la valeur par défaut de gunicorn
# (30 s) : le téléchargement d'un document volumineux (jusqu'à 300 Mo,
# voir MAX_UPLOAD_SIZE_MB) peut légitimement prendre plus de 30 s sur un
# réseau modeste.
timeout = 60

# Garde la connexion TCP ouverte brièvement entre deux requêtes du même
# client (le frontend Next.js, qui interroge le Backend à chaque
# navigation) — évite de renégocier une connexion complète à chaque appel.
keepalive = 5
