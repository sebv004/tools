# exo-imapcopy

Copy mail between two Exchange Online mailboxes over IMAP, from Linux or macOS.
Asks for what it needs, remembers the answers, and runs a dry run unless you
tell it otherwise.

Written because **there is no supported server-side mailbox-to-mailbox copy in
Exchange Online**. `Search-Mailbox -TargetMailbox` was retired in April 2024,
`New-ComplianceSearchAction -Export` had its export parameters disabled on
26 May 2025, and Microsoft's own retirement docs answer "copy messages from one
mailbox to a different mailbox" with *assign permissions to the mailbox and let
a client do it*. This is that client, scripted.

## Requirements

```bash
brew install powershell imapsync   # imapsync required; pwsh for the setup steps
# jq, curl and python3 are also used, and are usually already present
```

## Usage

```bash
exo-imapcopy               # ask, then dry run — nothing is written
exo-imapcopy --go          # ask, then actually copy
exo-imapcopy --diag        # sign in, print what the token may do, stop
exo-imapcopy --setup       # print the tenant setup steps
exo-imapcopy --delegated   # sign in as a user with a device code
exo-imapcopy --app         # sign in as the app itself (default)
exo-imapcopy --relogin     # forget the cached login, sign in again
exo-imapcopy --move-uids   # move a UID range between folders in ONE mailbox
exo-imapcopy --reset       # forget saved settings

exo-imapcopy -- --maxage 30      # anything after -- goes to imapsync verbatim
```

Answers are cached in `~/.config/exo-imapcopy.env`, mode 600. The script refuses
to read that file if it is group- or world-readable.

Prompts: source mailbox, target mailbox, all folders or one, target folder name,
flatten or nest, whether to skip non-mail folders, and whether to remember.

### Copying everything

Choosing *Everything* then *keep the original folder names* gives you:

```
target-mailbox/
└── Imported/
    ├── INBOX
    ├── Archive
    ├── Sent Items
    └── ...
```

Non-mail folders (Calendar, Contacts, Tasks, Notes, Journal, Outbox,
Conversation History) are skipped by default — IMAP exposes them but their items
are appointments and contact cards, not mail, so copying them errors or lands
unreadable items.

`Deleted Items` and `Junk Email` *are* copied, being real mail folders. To skip
them: `exo-imapcopy -- --exclude '^(Deleted Items|Junk Email|Trash)$'`

## Choosing a sign-in mode

|  | `--app` (default) | `--delegated` |
|---|---|---|
| Acts as | the app registration itself | a signed-in user |
| Login | silent, scriptable, cron-friendly | device code, interactive |
| Entra permission | `IMAP.AccessAsApp` (Application) | `IMAP.AccessAsUser.All` (Delegated) |
| Admin consent | required, grants tenant-wide mail access | usually consented at sign-in |
| `New-ServicePrincipal` | required | not needed |
| Needs a mailbox? | no | **yes** — the signing-in account must have one |
| Client secret | required | not needed |

`--delegated` is the lower-privilege option and the quicker one to set up.
`--app` is the one to use for unattended runs.

Both modes need an app registration, because OAuth needs a client ID. Basic
authentication is gone; there is no username/password route.

---

# Creating the app registration

## Common steps (both modes)

**1. Open the Entra admin center**

<https://entra.microsoft.com>, signed in with a Microsoft 365 admin account.
App registrations are part of the free Entra tier included with every M365
subscription — no Azure subscription, no billing.

If you can't find it: <https://admin.microsoft.com> → *Show all* → under
**Admin centers** → **Identity**. Direct link to the list:
`https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade`

**2. Register the app**

**Identity** → **Applications** → **App registrations** → **New registration**

| Setting | Value |
|---|---|
| Name | `exo-imapcopy` |
| Supported account types | **Accounts in this organizational directory only** (single tenant) |
| Redirect URI | leave empty |

**3. Copy two IDs from the Overview page**

| Overview field | Script prompt |
|---|---|
| **Application (client) ID** | App (client) ID |
| **Directory (tenant) ID** | Tenant ID |

Then follow **one** of the two sections below.

## delegated mode

**4. Enable public client flows**

**Authentication** → *Advanced settings* → **Allow public client flows** = **Yes**

Device code sign-in fails without this, with
`AADSTS7000218: The request body must contain the following parameter: client_assertion or client_secret.`

**5. API permission — usually nothing to do**

Delegated scopes are consented when you sign in, so
`https://outlook.office.com/IMAP.AccessAsUser.All` does not need
pre-registering. Run `exo-imapcopy --delegated --diag` and approve the prompt.

Only if your tenant blocks user consent:

**API permissions** → **Add a permission** → **APIs my organization uses** tab →
search `Office 365 Exchange Online` → **Delegated permissions** → expand the
**IMAP** group → tick **IMAP.AccessAsUser.All** → **Add permissions** →
**Grant admin consent**.

Two traps here:

- The *Select an API* search box matches **API names**, not permission names.
  Typing `IMAP.AccessAsUser.All` into it returns nothing. Search for
  `Office 365 Exchange Online`, or its fixed ID
  `00000002-0000-0ff1-ce00-000000000000`.
- The *Select permissions* box matches **group names**. Clear it and expand the
  groups; `IMAP` is not where alphabetical order would put it.

No client secret is needed in this mode.

**6. Grant the signing-in account access to the mailboxes**

Being a Global or Exchange admin does **not** grant access to mailbox contents,
and the signing-in account **must have a mailbox of its own** — a licence-free
admin account authenticates fine and then fails with
`NO User is authenticated but not connected.`

```powershell
Install-Module ExchangeOnlineManagement -Scope CurrentUser   # first time only
Connect-ExchangeOnline -UserPrincipalName you@yourdomain

# not needed for a mailbox you already own
Add-MailboxPermission -Identity <target-mailbox> `
  -User <your-upn> -AccessRights FullAccess
```

## app mode

**4. Create a client secret**

**Certificates & secrets** → **Client secrets** → **New client secret**

Copy the **Value** column immediately — it is shown once only. **Secret ID** is
the wrong column. Note the expiry; when it lapses, sign-in fails with
`AADSTS7000215: Invalid client secret provided.`

**5. Add the application permission**

**API permissions** → **Add a permission** → **APIs my organization uses** tab →
`Office 365 Exchange Online` → **Application permissions** → **IMAP.AccessAsApp**
→ **Add permissions** → **Grant admin consent**.

**6. Get the service principal Object ID**

**Enterprise applications** → your app → **Overview** → **Object ID**

This is **not** the Object ID on the App registrations page. They are different
GUIDs for the same app, and the wrong one causes an authentication failure with
no useful error.

**7. Register it in Exchange and scope it to the mailboxes**

```powershell
Connect-ExchangeOnline -UserPrincipalName you@yourdomain

New-ServicePrincipal -AppId <client-id> -ObjectId <sp-object-id> `
  -DisplayName "exo-imapcopy"

Add-MailboxPermission -Identity <source-mailbox> `
  -User <sp-object-id> -AccessRights FullAccess
Add-MailboxPermission -Identity <target-mailbox> `
  -User <sp-object-id> -AccessRights FullAccess
```

Grant FullAccess on **only** the mailboxes involved. `IMAP.AccessAsApp` plus a
broad grant turns this app into a tenant-wide mail-reading credential; the
per-mailbox grant is what contains it.

## Both modes: check IMAP is enabled

```powershell
Get-CASMailbox -Identity <mailbox> | Format-List ImapEnabled
Set-CASMailbox -Identity <mailbox> -ImapEnabled $true    # if False
```

---

# Troubleshooting

Start with `exo-imapcopy --diag`. It signs in, decodes the token, and prints the
`roles` (app mode) or `scp` (delegated) claim, so you can tell an Entra problem
from an Exchange one.

| Symptom | Cause |
|---|---|
| `AADSTS7000218 ... client_assertion or client_secret` | delegated: **Allow public client flows** is not Yes |
| `AADSTS7000215: Invalid client secret` | app mode: secret wrong or expired |
| `--diag` shows no `IMAP.AccessAsApp` | app mode: permission or admin consent missing |
| `NO AUTHENTICATE failed` | token carries no IMAP authority — check `--diag`, then `New-ServicePrincipal` |
| `NO User is authenticated but not connected` | IMAP disabled on the mailbox, **or** the signing-in account has no mailbox |
| `NO Login failed` | mailbox access not granted (`Add-MailboxPermission`) |
| `[TRYCREATE] The destination mailbox could not be found` | target folder missing; `--move-uids` now creates it |

## Notes

- The access token lasts about an hour. imapsync skips messages already present,
  so if a large copy outruns the token, just run it again — nothing duplicates.
- `--move-uids` repairs messages copied into the wrong folder. It uses IMAP
  `UID MOVE`, falls back to `COPY` + `\Deleted` + `EXPUNGE`, checks every step,
  and counts both folders afterwards. Run it without `--go` first.
- Outlook and OWA cache folder contents. After a copy or move, a stale client
  can still show the old state — refresh before concluding something failed.
- `INBOX` is special-cased by imapsync and is not covered by `--prefix2`, which
  would drop the source Inbox into the target's real Inbox. Nested mode uses
  `--regextrans2 "s{^}{<folder>/}" --nofixInboxINBOX` instead.
