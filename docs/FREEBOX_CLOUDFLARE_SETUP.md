# Guide de liaison sécurisée : Freebox VM ↔ mykairn.fr (Cloudflare Tunnel Zero-Port)

Ce guide permet d'exposer `mykairn-sciwatch` (port local `8095` sur la VM Freebox `192.168.1.170`) à l'application `mykairn.fr` **sans ouvrir aucun port entrant sur la Freebox**, tout en gardant l'accès direct libre sur votre réseau Wi-Fi local.

---

## 1. Sur la VM Freebox (`192.168.1.170`)

1. **Changer le mot de passe SSH par défaut et installer une clé SSH** :
   ```bash
   passwd freebox
   ```
2. **Configurer `.env` dans `/opt/mykairn-sciwatch/.env`** :
   ```env
   SCIWATCH_API_SECRET=<generer-avec-openssl-rand-hex-32>
   SCIWATCH_ALLOW_LAN_DIRECT=true
   SCIWATCH_TRUSTED_LAN_PREFIXES=192.168.,10.
   SCIWATCH_CORS_ORIGIN=https://mykairn.fr
   MYKAIRN_WEBHOOK_URL=https://mykairn.fr/api/sciwatch/webhook
   MYKAIRN_WEBHOOK_SECRET=<meme-secret-ou-secret-dedie>
   ```
   *(Redémarrer le service : `sudo systemctl restart mykairn-sciwatch-web.service`)*

3. **Installer `cloudflared` (tunnel sortant léger)** :
   ```bash
   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
   sudo install /tmp/cloudflared /usr/local/bin/cloudflared && rm -f /tmp/cloudflared
   ```

---

## 2. Sur Cloudflare Zero Trust (`mykairn.fr`)

1. **Zero Trust → Networks → Tunnels → Create a tunnel** (`Cloudflared`), nom `sciwatch-freebox`.
2. Copier le token et l'enregistrer sur la VM dans `/etc/mykairn-sciwatch-tunnel.env` :
   ```env
   CF_TUNNEL_TOKEN=<votre-token-tunnel>
   ```
   Puis activer l'unité :
   ```bash
   sudo cp /opt/mykairn-sciwatch/systemd/cloudflared-sciwatch.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now cloudflared-sciwatch.service
   ```
3. **Public Hostname** du tunnel :
   - Sous-domaine : `sciwatch-origin.mykairn.fr`
   - Service Type : `HTTP`, URL : `http://127.0.0.1:8095`
4. **Zero Trust → Access → Service Auth → Service Tokens** :
   - Créer un Service Token `mykairn-fr-bff` (noter `CF-Access-Client-Id` et `CF-Access-Client-Secret`).
   - Créer une Application Self-Hosted sur `sciwatch-origin.mykairn.fr` avec Policy **Action: Service Auth** autorisant uniquement ce Service Token.

---

## 3. Sur Vercel (`mykairn.fr`)

Ajouter ces variables d'environnement en Production :
- `SCIWATCH_UPSTREAM_URL=https://sciwatch-origin.mykairn.fr`
- `SCIWATCH_API_SECRET=<meme secret que sur la Freebox>`
- `CF_ACCESS_CLIENT_ID=<Client ID du Service Token>`
- `CF_ACCESS_CLIENT_SECRET=<Client Secret du Service Token>`
