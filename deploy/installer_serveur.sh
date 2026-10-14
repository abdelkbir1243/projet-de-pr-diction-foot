#!/usr/bin/env bash
# Préparation et sécurisation d'un serveur Ubuntu 22.04 / 24.04 pour Goalgebra. À lancer une seule fois, en root :
#     sudo bash deploy/installer_serveur.sh <utilisateur>
# Effets : mises à jour de sécurité automatiques · pare-feu (SSH, HTTP, HTTPS seulement) · fail2ban · Docker ·
#          utilisateur de déploiement · SSH par clé uniquement (si une clé est déjà installée, pour ne pas te bloquer dehors).
set -euo pipefail

UTILISATEUR="${1:-goalgebra}"
[ "$(id -u)" -eq 0 ] || { echo "À lancer avec sudo."; exit 1; }

echo "== Mises à jour et paquets de sécurité"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg ufw fail2ban unattended-upgrades git
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "== Pare-feu : seuls SSH (22), HTTP (80) et HTTPS (443) sont ouverts"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

echo "== fail2ban (bannit les IP qui essaient des mots de passe SSH)"
cat > /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable --now fail2ban

echo "== Docker (dépôt officiel)"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
# Docker contourne ufw pour les ports publiés : seul Caddy publie des ports (80/443), la base et les services restent internes.
cat > /etc/docker/daemon.json <<'EOF'
{ "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "5" }, "live-restore": true }
EOF
systemctl restart docker

echo "== Utilisateur de déploiement : $UTILISATEUR"
id "$UTILISATEUR" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "$UTILISATEUR"
usermod -aG docker "$UTILISATEUR"
if [ -f /root/.ssh/authorized_keys ] && [ ! -f "/home/$UTILISATEUR/.ssh/authorized_keys" ]; then
  install -d -m 700 -o "$UTILISATEUR" -g "$UTILISATEUR" "/home/$UTILISATEUR/.ssh"
  install -m 600 -o "$UTILISATEUR" -g "$UTILISATEUR" /root/.ssh/authorized_keys "/home/$UTILISATEUR/.ssh/authorized_keys"
fi

echo "== SSH : connexion par clé uniquement, pas de connexion root"
if [ -s "/home/$UTILISATEUR/.ssh/authorized_keys" ]; then
  cat > /etc/ssh/sshd_config.d/90-goalgebra.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
MaxAuthTries 3
EOF
  systemctl reload ssh || systemctl reload sshd
  echo "SSH durci. Vérifie dans un AUTRE terminal : ssh $UTILISATEUR@<ip> avant de fermer celui-ci."
else
  echo "⚠ Aucune clé SSH trouvée pour $UTILISATEUR : SSH n'a PAS été durci (ajoute ta clé puis relance le script)."
fi

echo "== Terminé. Étapes suivantes (en tant que $UTILISATEUR) : voir docs/deploiement_serveur.md"
