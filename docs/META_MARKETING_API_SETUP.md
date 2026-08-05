# Meta Marketing API & Graph API Production Setup Guide

This document explains how to set up your official **Meta App**, **System User**, **Facebook OAuth**, and **Webhooks** for MetaMind AI on your Hostinger VPS.

---

## 1. Create a Meta Developer App

1. Go to [developers.facebook.com](https://developers.facebook.com/) and log in with your Facebook account.
2. Click **My Apps** > **Create App**.
3. Select **Other** > **Business** app type.
4. Name your app **MetaMind AI OS** and link your Meta Business Manager.

---

## 2. Configure Products & Permissions

Add the following Meta products to your App:
- **Marketing API**: For campaign management, Advantage+ Shopping, ad sets, and creative uploads.
- **Facebook Login for Business**: For client OAuth authentication.
- **Webhooks**: For real-time notifications on campaign status changes and lead ads.

### Required Permissions:
- `ads_management`
- `ads_read`
- `business_management`
- `read_insights`
- `pages_show_list`
- `instagram_basic`

---

## 3. Set Up Facebook OAuth Redirect URIs

In **Facebook Login for Business Settings**:
1. Enable **Client OAuth Login** and **Web OAuth Login**.
2. Add your custom domain redirect URI:
   ```
   https://yourdomain.com/api/auth/facebook/callback
   ```

---

## 4. Set Up Real-Time Webhooks

In **Meta Developer Dashboard > Webhooks**:
1. Select **Ad Account** or **Page** object.
2. Enter your Webhook Callback URL:
   ```
   https://yourdomain.com/api/webhooks/meta
   ```
3. Enter your `META_WEBHOOK_VERIFY_TOKEN` (matching your `.env` value).
4. Click **Verify and Save**.

---

## 5. Generate a System User Long-Lived Access Token

For automated server-to-server Celery background jobs:
1. Open **Meta Business Settings** > **Users** > **System Users**.
2. Click **Add** > Role: **Admin**.
3. Click **Assign Assets** and grant full access to your Ad Accounts.
4. Click **Generate New Token**, select `ads_management`, `ads_read`, and `read_insights`.
5. Select **Never Expire** token option.
6. Copy this token into `.env` under `META_SYSTEM_USER_TOKEN`.
