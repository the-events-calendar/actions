# The Events Calendar: GitHub Actions

This repository contains the code for the Automations using GitHub Actions used by the The Events Calendar team.

Our goal here is to create Actions that will allow us to deprecate the use of our Internal Jenkins for most of the automation tasks.

Before the creation of this repository most of the automation were done with individual GitHub Actions that were scattered across the different repositories. This made it hard to maintain and to have a clear overview of what was happening.

For more global integrations we used Jenkins, but we want to move away from it and use GitHub Actions for everything.

## Sychronization of Files

We are using the [BetaHuhn/repo-file-sync-action](https://github.com/marketplace/actions/repo-file-sync-action) action to enable us to sychronize files across different repositories.

So any files that need to be identical across different repositories can be sychronized using this action, and the original stored in this repository under the `templates` folder.

> [!NOTE]
> If you are using this action, please make sure to include `@tec-bot` user as a collaborator with write permissions in the repository you want to sync the files to.