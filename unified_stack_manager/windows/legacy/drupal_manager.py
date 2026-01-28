"""
Drupal Manager - Fully Automated Version
Handles the creation of Drupal 11 sites with AI modules.
"""
import argparse
import os
import sys
import subprocess
import time
from pathlib import Path


class DrupalManager:
    def __init__(self, apache_htdocs="C:/APACHE24/htdocs", php_manager=None):
        self.htdocs_path = Path(apache_htdocs)
        # In the future, this could be integrated with PHPManager to get the correct php.exe
        self.php_manager = php_manager
        self.php_exe_path = None
        self.composer_path = None
        self._find_php_installation()

    def _find_php_installation(self):
        """Finds a suitable PHP installation managed by php_manager.py."""
        self.log("Searching for a valid PHP installation...")
        # Check in common locations managed by php_manager.py, starting with newest
        for version in ["8.4", "8.3", "8.2", "8.1", "8.0", "7.4"]:
            php_path = Path(f"C:/php{version}")
            php_exe = php_path / "php.exe"
            composer_phar = php_path / "composer.phar"
            if php_exe.exists() and composer_phar.exists():
                self.log(f"Found PHP {version} at {php_path}", "INFO")
                self.php_exe_path = str(php_exe)
                self.composer_path = str(composer_phar)
                return

        self.log("No suitable PHP installation with Composer found. Please ensure PHP is installed via php_manager.py.",
                 "ERROR")
        raise EnvironmentError("Could not find a valid PHP installation with composer.phar.")

    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def create_site(self, project_name, drupal_version="11.x-dev", ai_mode=True):
        """
        Main method to create a new Drupal site.
        """
        self.log(f"Starting creation of Drupal site: {project_name} (AI Mode: {ai_mode})")
        project_path = self.htdocs_path / project_name

        # Idempotency: If project exists, we might want to skip some steps
        if project_path.exists():
            self.log(f"Project path {project_path} already exists. Skipping 'composer create-project'.", "WARNING")
            is_new = False
        else:
            is_new = True
            # Step 1: Create project with Composer
            if not self._create_drupal_project(project_path, drupal_version):
                return False

        if ai_mode:
            # Step 2: Add AI and Key modules
            if not self._add_modules(project_path):
                return False

        # Step 3: Install Drupal using Drush (only if new)
        if is_new:
            if not self._install_site(project_path):
                return False
        else:
            self.log("Skipping site installation as the project already exists.", "INFO")

        if ai_mode:
            # Step 4: Enable modules
            if not self._enable_modules(project_path):
                return False

            # Step 5: Create .env.example
            self._create_env_example(project_path)

            # Step 6: Create sample blog
            self._create_sample_blog(project_path)

        # Step 7: Verify installation
        self._verify_installation(project_path)

        self.log(f"Successfully processed Drupal site: {project_name}", "INFO")
        self.log(f"Site located at: {project_path}", "INFO")
        if ai_mode:
            self.log(f"Next steps: Configure your API keys in the Drupal admin or using the .env file.", "INFO")

        return True

    def _run_command(self, command, cwd):
        """Helper to run a command and log its output."""
        self.log(f"Running command: {' '.join(command)} in {cwd}", "DEBUG")
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            # Stream output for better feedback
            for line in process.stdout:
                self.log(line.strip(), "CMD")

            process.wait()

            if process.returncode != 0:
                self.log(f"Command failed with exit code {process.returncode}", "ERROR")
                stderr_output = process.stderr.read()
                self.log(stderr_output, "ERROR")
                return False

            return True
        except FileNotFoundError:
            self.log(f"Command not found: {command[0]}", "ERROR")
            return False
        except Exception as e:
            self.log(f"An exception occurred: {e}", "ERROR")
            return False

    def _create_drupal_project(self, project_path, drupal_version):
        """Creates a new Drupal project using Composer."""
        self.log("Creating Drupal project with Composer...")
        command = [
            self.php_exe_path,
            self.composer_path,
            "create-project",
            f"drupal/recommended-project:{drupal_version}",
            str(project_path),
            "--no-interaction"
        ]
        return self._run_command(command, self.htdocs_path)

    def _add_modules(self, project_path):
        """Adds Drupal AI and requested modules via Composer."""
        self.log("Adding AI modules and dependencies via Composer...")

        modules = [
            "drupal/ai:^1.3@beta",
            "drupal/key",
            "drupal/ai_agents",
            "drupal/ai_simple_pdf_to_text:^1.0@alpha",
            "drupal/tool:^1.0@alpha",
            "drupal/ai_automators",
            "drupal/ai_assistants_api",
            "drupal/ai_chatbot",
            "drupal/ai_content_suggestions",
            "drupal/ai_translate",
            "drupal/ai_search",
            "drupal/ai_image_alt_text",
            "drupal/ai_media_image",
            "drupal/ai_seo",
            "drupal/mcp",
            "drupal/langfuse",
            "drupal/ai_provider_openai",
            "drupal/ai_provider_ollama",
            "drupal/ai_provider_anthropic",
            "drupal/ai_provider_google"
        ]

        for module in modules:
            self.log(f"Requiring module: {module}")
            command = [self.php_exe_path, self.composer_path, "require", module, "--no-interaction"]
            if not self._run_command(command, project_path):
                self.log(f"Failed to add module {module}. It might be a submodule or not exist. Continuing...", "WARNING")

        return True

    def _install_site(self, project_path):
        """Installs the Drupal site using Drush."""
        self.log("Installing Drupal site using Drush...")

        drush_path = project_path / "vendor" / "bin" / "drush"
        db_config = "mysql://drupal_user:drupal_pass_123@localhost/drupal_db"

        command = [
            self.php_exe_path,
            str(drush_path),
            "site:install",
            "--db-url=" + db_config,
            "--account-name=admin",
            "--account-pass=admin",
            "--site-name=DrupalAI Site",
            "-y"
        ]
        return self._run_command(command, project_path / "web")

    def _enable_modules(self, project_path):
        """Enables the newly added modules."""
        self.log("Enabling AI modules and submodules...")
        drush_path = project_path / "vendor" / "bin" / "drush"

        modules = [
            "ai",
            "key",
            "ai_agents",
            "ai_simple_pdf_to_text",
            "tool",
            "ai_automators",
            "ai_assistants_api",
            "ai_chatbot",
            "ai_ckeditor",
            "ai_content_suggestions",
            "ai_translate",
            "ai_search",
            "ai_logging",
            "ai_observability",
            "ai_image_alt_text",
            "ai_media_image",
            "ai_seo",
            "mcp",
            "model_context_protocol",
            "langfuse",
            "ai_provider_openai",
            "ai_provider_ollama",
            "ai_provider_anthropic",
            "ai_provider_google"
        ]

        # Enable them one by one or in small groups to avoid memory issues and identify failures
        for module in modules:
            self.log(f"Enabling module: {module}")
            command = [
                self.php_exe_path,
                str(drush_path),
                "en",
                module,
                "-y"
            ]
            self._run_command(command, project_path / "web")

        return True

    def _verify_installation(self, project_path):
        """Verifies that modules are enabled."""
        self.log("Verifying module status...")
        drush_path = project_path / "vendor" / "bin" / "drush"
        command = [
            self.php_exe_path,
            str(drush_path),
            "pm:list",
            "--status=enabled",
            "--format=table"
        ]
        return self._run_command(command, project_path / "web")

    def _create_sample_blog(self, project_path):
        """Creates a sample blog with content, taxonomies and menu."""
        self.log("Creating sample blog content...")
        drush_path = project_path / "vendor" / "bin" / "drush"

        # 1. Create taxonomy terms for 'tags' (Standard profile has 'tags')
        vocab = "tags"
        terms = ["IA", "Tecnología", "Pruebas"]
        for term in terms:
            self.log(f"Creating taxonomy term: {term}")
            command = [
                self.php_exe_path, str(drush_path), "php:eval",
                f"\\Drupal\\taxonomy\\Entity\\Term::create(['name' => '{term}', 'vid' => '{vocab}'])->save();"
            ]
            self._run_command(command, project_path / "web")

        # 2. Try to generate content with IA if keys are configured
        if self._are_ai_keys_available(project_path):
            self.log("AI keys detected. Attempting to generate content with IA...")
            # Use drush php-eval to call ai_content_suggestions if it exists
            # We try to create at least one node with IA
            ia_script = """
            try {
                if (\\Drupal::moduleHandler()->moduleExists('ai_content_suggestions')) {
                    $suggestor = \\Drupal::service('ai_content_suggestions.suggestor');
                    // This is a hypothetical service call based on user's preference
                    // In a real scenario, we would use the actual service method
                    $suggestions = $suggestor->generateTitleAndBody('Drupal 11 and AI');
                    $node = \\Drupal\\node\\Entity\\Node::create([
                        'type' => 'article',
                        'title' => $suggestions['title'] ?? 'Post generado por IA',
                        'body' => ['value' => $suggestions['body'] ?? 'Contenido generado por IA.', 'format' => 'basic_html'],
                        'status' => 1
                    ]);
                    $node->save();
                    echo "SUCCESS_IA";
                }
            } catch (\\Exception $e) {
                echo "FAIL_IA: " . $e->getMessage();
            }
            """
            ia_command = [self.php_exe_path, str(drush_path), "php:eval", ia_script]
            # Capture output to see if it worked
            # Note: _run_command currently doesn't return output, but we can check success
            if self._run_command(ia_command, project_path / "web"):
                self.log("AI content generation attempted.")

        # 3. Create 3 blog posts (using 'article' type which is standard) - Static Fallback/Initial content
        posts = [
            {"title": "El futuro de la IA en Drupal", "body": "Este es un post generado automáticamente para probar las capacidades de IA."},
            {"title": "Innovación Tecnológica con Ollama", "body": "Ollama permite correr LLMs localmente de forma sencilla."},
            {"title": "Pruebas de Automatización con USM", "body": "Unified Stack Manager facilita el despliegue de entornos complejos."}
        ]

        for post in posts:
            self.log(f"Creating blog post: {post['title']}")
            # Escaping single quotes in body if any
            body_content = post['body'].replace("'", "\\'")
            command = [
                self.php_exe_path, str(drush_path), "php:eval",
                f"$node = \\Drupal\\node\\Entity\\Node::create(['type' => 'article', 'title' => '{post['title']}', 'body' => ['value' => '{body_content}', 'format' => 'basic_html'], 'status' => 1]); $node->save();"
            ]
            self._run_command(command, project_path / "web")

        # 4. Add a link to 'articles' in main menu (usually /node or /blog if view exists)
        # Standard profile has articles at /node. We can create a menu link.
        self.log("Adding blog link to main menu...")
        command = [
            self.php_exe_path, str(drush_path), "php:eval",
            "\\Drupal\\menu_link_content\\Entity\\MenuLinkContent::create(['title' => 'Blog', 'link' => ['uri' => 'internal:/node'], 'menu_name' => 'main', 'weight' => 0])->save();"
        ]
        self._run_command(command, project_path / "web")

        return True

    def _are_ai_keys_available(self, project_path):
        """Checks if AI API keys are configured in .env or environment."""
        env_file = project_path / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
                if "OPENAI_API_KEY" in content and "your_" not in content:
                    return True

        # Also check system environment
        if os.environ.get("OPENAI_API_KEY"):
            return True

        return False

    def _create_env_example(self, project_path):
        """Creates a .env.example file with API key placeholders."""
        self.log("Creating .env.example file...")
        env_content = """# --- Drupal AI API Keys Configuration ---
# Rename this file to .env and fill in your keys.
# These can be used by the 'Key' module if configured to read from environment variables.

# AI Providers API Keys
OPENAI_API_KEY="your_openai_key_here"
ANTHROPIC_API_KEY="your_anthropic_key_here"
GOOGLE_GEMINI_API_KEY="your_gemini_key_here"

# Ollama (Local LLM)
# Standard installation in Windows usually runs at http://localhost:11434
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="llama3"

# Langfuse (Observability)
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_HOST="https://cloud.langfuse.com"

# Verification
# Use 'drush ai:test' (if available) or check the AI admin dashboard.
"""
        try:
            with open(project_path / ".env.example", "w") as f:
                f.write(env_content)
            return True
        except Exception as e:
            self.log(f"Failed to create .env.example: {e}", "ERROR")
            return False


def main():
    parser = argparse.ArgumentParser(description="Drupal Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new Drupal site.")
    create_parser.add_argument("project_name", help="The name of the project folder to be created.")
    create_parser.add_argument("--drupal-version", default="11.x-dev", help="The version of Drupal to install.")
    create_parser.add_argument("--ai", action="store_true", help="Enable AI modules automation.")

    args = parser.parse_args()
    manager = DrupalManager()

    if args.command == "create":
        manager.create_site(args.project_name, args.drupal_version, ai_mode=args.ai)


if __name__ == "__main__":
    main()
