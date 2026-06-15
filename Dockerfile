# 1. Image de base (Python 3.11 sur Debian 12)
FROM python:3.11-slim-bookworm

# 2. Définir le répertoire de travail à l'intérieur du conteneur
WORKDIR /app

# 3. Copier les dépendances en premier (Optimisation du cache Docker)
COPY requirements.txt .

# 4. Installer les dépendances Python sans garder de cache pour alléger l'image
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copier le reste du code source du projet
COPY . .

# 6. Exposer le port par défaut utilisé par Streamlit
EXPOSE 8501

# 7. Commande pour démarrer l'application HYDRA
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]