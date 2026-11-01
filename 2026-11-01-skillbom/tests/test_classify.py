import unittest

from skillbom.classify import classify_text


def caps(text):
    return classify_text(text).capabilities


class NetworkSignals(unittest.TestCase):
    def test_curl(self):
        self.assertIn("network", caps('curl -sS "https://example.com/api"\n'))

    def test_wget(self):
        self.assertIn("network", caps("wget -qO- https://example.com\n"))

    def test_python_urllib(self):
        self.assertIn("network", caps("import urllib.request\nurllib.request.urlopen(url)\n"))

    def test_requests_library(self):
        self.assertIn("network", caps("import requests\nr = requests.get(url)\n"))

    def test_node_fetch(self):
        self.assertIn("network", caps("const r = await fetch(url);\n"))

    def test_prose_word_network_is_not_a_signal(self):
        self.assertEqual(classify_text("the network was down all morning\n").capabilities, frozenset())


class ExecSignals(unittest.TestCase):
    def test_subprocess(self):
        self.assertIn("exec", caps("import subprocess\nsubprocess.run(cmd)\n"))

    def test_os_system(self):
        self.assertIn("exec", caps("import os\nos.system('ls')\n"))

    def test_shell_dash_c(self):
        self.assertIn("exec", caps('sh -c "echo hi"\n'))

    def test_node_spawn(self):
        self.assertIn("exec", caps("const {spawnSync} = require('child_process');\n"))


class EvalSignals(unittest.TestCase):
    def test_python_eval(self):
        self.assertIn("code_eval", caps("result = eval(expr)\n"))

    def test_python_exec(self):
        self.assertIn("code_eval", caps("exec(source, env)\n"))

    def test_js_new_function(self):
        self.assertIn("code_eval", caps("const f = new Function('a', body);\n"))

    def test_unsafe_yaml_load(self):
        self.assertIn("code_eval", caps("data = yaml.load(text)\n"))

    def test_safe_yaml_load_is_not_eval(self):
        self.assertNotIn("code_eval", caps("data = yaml.safe_load(text)\n"))


class FileSignals(unittest.TestCase):
    def test_write_text(self):
        self.assertIn("fs_write", caps("Path(p).write_text('x')\n"))

    def test_open_for_write(self):
        self.assertIn("fs_write", caps("with open(p, 'w') as fh:\n    fh.write('x')\n"))

    def test_node_write_file(self):
        self.assertIn("fs_write", caps("fs.writeFileSync(p, data);\n"))

    def test_read_only_open_is_not_fs_write(self):
        self.assertNotIn("fs_write", caps("with open(p) as fh:\n    fh.read()\n"))


class CredentialSignals(unittest.TestCase):
    def test_environ_read(self):
        self.assertIn("credentials", caps("key = os.environ['OPENAI_API_KEY']\n"))

    def test_getenv(self):
        self.assertIn("credentials", caps("key = os.getenv('TOKEN')\n"))

    def test_dotenv_path(self):
        self.assertIn("credentials", caps("load_env('~/.hermes/.env')\n"))

    def test_api_key_name(self):
        self.assertIn("credentials", caps("KALSHI_API_KEY = 'x'\n"))

    def test_authorization_header(self):
        self.assertIn("credentials", caps('headers = {"Authorization": "Bearer " + t}\n'))


class HermesSurfaceSignals(unittest.TestCase):
    def test_dot_hermes_path(self):
        self.assertIn("hermes_surface", caps("p = Path.home() / '.hermes' / 'vault'\n"))

    def test_state_db(self):
        self.assertIn("hermes_surface", caps("sqlite3.connect('state.db')\n"))

    def test_profiles_path(self):
        self.assertIn("hermes_surface", caps("root = '~/.hermes/profiles'\n"))


class ClassificationShape(unittest.TestCase):
    def test_multiple_capabilities_and_stable_signal_order(self):
        text = "import subprocess, os\nos.environ['X']\nsubprocess.run(['curl','x'])\n"
        result = classify_text(text)
        self.assertEqual(result.capabilities, frozenset({"exec", "credentials", "network"}))
        self.assertEqual(list(result.signals), sorted(result.signals))

    def test_signals_are_unique(self):
        result = classify_text("curl a\ncurl b\ncurl c\n")
        self.assertEqual(result.signals.count("network:curl"), 1)

    def test_empty_text_is_clean(self):
        result = classify_text("")
        self.assertEqual(result.capabilities, frozenset())
        self.assertEqual(result.signals, ())


if __name__ == "__main__":
    unittest.main()
