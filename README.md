# Unified Stack Manager (USM)

Unified Stack Manager (USM) is a versatile command-line tool designed to streamline the setup and management of local development environments for Drupal. It provides a unified interface for both Windows (WAMP) and Linux (LAMP) stacks, automating repetitive tasks and ensuring consistency across platforms.

This tool is ideal for developers and system administrators who need to rapidly provision, configure, and manage web servers for Drupal projects.

## Features

-   **Cross-Platform**: Works on both Debian-based Linux (Ubuntu, Debian) and Windows.
-   **Full Stack Installation**: Installs Apache, MySQL/MariaDB, and multiple PHP versions.
-   **Automated Drupal Site Creation**: Creates Apache virtual hosts, databases, and installs Drupal with a single command.
-   **Multi-PHP Support**: Easily switch between different PHP versions for your projects.
-   **Safety First**:
    -   **Pre-execution Validation**: Checks for administrator/root permissions.
    -   **Dry-Run Mode**: Preview all changes before they are made.
-   **Configuration Driven**: Uses a central YAML file for configuration to avoid hardcoded values.
-   **Audit Logging**: Logs all actions for traceability.

## Requirements

-   **Operating System**:
    -   Debian-based Linux (e.g., Ubuntu 22.04 LTS)
    -   Windows 10/11
-   **Permissions**: `sudo` / Administrator access.
-   **Python**: Python 3.8+

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/dane-dc/unified-stack-manager.git
    cd unified-stack-manager
    ```

2.  **Install the package in editable mode:**
    This will install the necessary dependencies and make the `usm` command available in your terminal.
    ```bash
    pip install -e .
    ```
    On Linux, you might need to use `sudo`:
    ```bash
    sudo pip install -e .
    ```

## Usage

The main command is `usm`. You can see a list of all available commands by running:
```bash
usm --help
```

### Global Options

-   `--dry-run`: Simulate the command without making any changes to the system.
-   `--config FILE`: Use a custom configuration file.
-   `--verbose` or `-v`: Enable detailed output, useful for debugging.

---

### Commands

#### `install`
Installs stack components.

**Usage:**
```bash
usm install [OPTIONS] [COMPONENTS]...
```

**Components:** `apache`, `mysql`, `php`, `all`

**Example (Linux):**
```bash
sudo usm install all
```

**Example (Windows):**
```powershell
usm install apache php
```

---

#### `create-site`
Creates a new Drupal site.

**Usage:**
```bash
usm create-site [OPTIONS] SITE_NAME
```

**Options:**
-   `--php-version`: The PHP version to use (e.g., `8.2`). Defaults to `8.2`.
-   `--drupal-version`: The Drupal version to install (e.g., `^10`). Defaults to `^10`.

**Example:**
```bash
sudo usm create-site my-drupal-site.local --php-version 8.2
```
The script will create the necessary virtual host, database, and download Drupal. At the end, it will display the database credentials. **Make sure to save the password!**

---

#### `list-sites`
Lists all created sites.

**Usage:**
```bash
usm list-sites
```

---

#### `switch-php`
Switches the PHP version for a specific site.

**Usage:**
```bash
usm switch-php [OPTIONS] SITE_NAME PHP_VERSION
```

**PHP Versions:** `7.4`, `8.1`, `8.2`, `8.3`

**Example:**
```bash
sudo usm switch-php my-drupal-site.local 8.1
```

---

#### `status`
Shows the status of the system components (e.g., Apache, MySQL services).

**Usage:**
```bash
usm status
```
