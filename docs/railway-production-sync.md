# Railway production UX and asset synchronization

## Runtime assets

The Docker build runs `bench build --production` and stores the resulting
`sites/assets` tree in the image. On startup, the entrypoint overlays that
tree onto the persistent `sites/assets` directory. Files with the same name
are refreshed from the image so `assets.json`, CSS/JS bundles, and app asset
links match the deployed image. Files not present in the image are retained;
the entrypoint does not delete the persistent asset directory.

The entrypoint also invalidates Frappe's shared `assets_json` cache for an
existing site. This does not synchronize database-backed Desk configuration.

## Desk, workspaces, and permissions

The app's standard DocTypes, Pages, Workspaces, and navigation definitions are
version-controlled under `apps/transport_management/transport_management`.
The app's `patches.txt` also lists these migration patches:

- `align_al_rana_workspace_permissions` changes custom DocType permissions and
  page roles.
- `setup_al_rana_native_ux` creates/updates module profiles and assigns module
  profiles and default workspaces to existing enabled users based on roles.
- `setup_al_rana_workspace_daily_home` creates or updates number cards,
  dashboard charts, and workspace cards, shortcuts, and quick lists.

These patches can change production database records and user access. Normal
Railway startup intentionally does not run `bench migrate`, so deploying a new
image alone does not execute them or synchronize changed standard metadata into
the database.

## Approval-gated production procedure

Before any database synchronization:

1. Compare the target site's installed apps, current Desk/workspace records,
   page roles, custom permissions, module profiles, and affected user defaults
   with the intended release.
2. Review the migration patch source and its effects on the actual production
   roles and users. In particular, confirm the profile/default-workspace
   assignments are approved.
3. Take and verify a production database backup, schedule a maintenance window,
   and obtain explicit approval for the migration.
4. Only after approval, run the repository's explicit
   `scripts/railway-migrate.sh` operation as a separately controlled task.
   This runs `bench migrate`, the TMS post-migrate setup, conditional
   `dispatch_portal` setup only if that app is already installed, and cache
   clearing. It does not install `dispatch_portal` or HRMS.
5. Verify the intended workspaces, navigation, page access, and affected user
   defaults with representative authorized accounts.

Do not attach the migration operation to image build or normal deployment
startup. Do not install HRMS or `dispatch_portal`, enable workers/scheduler,
or alter restored files/data as part of this synchronization without separate
approval.

## Verification limitations

Image-level asset refresh is covered by the Docker workflow's mounted-volume
smoke test. Application parity still requires authenticated comparison of the
localhost and production Desk, installed apps, database-backed workspaces,
permissions, and representative TMS screens. A successful image build alone
does not establish that parity.
