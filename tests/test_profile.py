import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_profile import ROOT, build, load, valid_url
from profile_ui import document, module, text_width, wrap


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(str(ROOT/'profile'), str(self.root/'profile'))
        shutil.copytree(str(ROOT/'templates'), str(self.root/'templates'))

    def change(self, name, mutate):
        path = self.root/name
        data = json.loads(path.read_text(encoding='utf-8'))
        mutate(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def test_all_assets_are_safe_valid_self_contained_svg(self):
        outputs = build(self.root)
        for name, content in outputs.items():
            if name.endswith('.svg'):
                svg = ET.fromstring(content)
                self.assertGreater(float(svg.attrib['height']), 0)
                for element in svg.iter():
                    tag = element.tag.rsplit('}', 1)[-1]
                    self.assertNotIn(tag, ['script', 'foreignObject', 'image', 'a'])
                    self.assertFalse(any(a.startswith('on') for a in element.attrib))
        self.assertEqual(outputs, build(self.root))

    def test_text_escaping_and_full_copyable_uid(self):
        label = '研究 <AI> & "工具"'
        self.change('profile/modules/about.json', lambda d: d['items'][0].update(value=label))
        self.change('profile/modules/games.json', lambda d: d['items'][0].update(uid='123456789012345'))
        result = build(self.root)
        self.assertIn('123456789012345', result['README.md'])
        self.assertIn('研究 &lt;AI&gt; &amp; &quot;工具&quot;', result['README.md'])
        self.assertIn(label, ''.join(ET.fromstring(result['assets/generated/module-about.svg']).itertext()))

    def test_long_content_increases_height_without_loss(self):
        profile, modules, _ = load(self.root)
        original = modules['about']
        _, short_height = module(original, 490, profile['theme'])
        long = copy.deepcopy(original)
        long['items'][0]['value'] = '长文本和LongUnbrokenIdentifier测试 ' * 20
        fragment, height = module(long, 490, profile['theme'])
        self.assertGreater(height, short_height)
        xml = ET.fromstring(document(fragment, 490, height, 'Long', profile['theme']))
        for element in xml.iter():
            if element.tag.endswith('text'):
                self.assertLess(float(element.attrib['y']), height)
        for line in wrap(long['items'][0]['value'], 296, 21):
            self.assertLessEqual(text_width(line, 21), 296)

    def test_add_disable_and_reorder_without_renderer_changes(self):
        path = self.root/'profile/modules/books.json'
        path.write_text(json.dumps({'type':'cards','title':'书架','items':[{'title':'书名','body':'读书笔记'}]}), encoding='utf-8')
        self.change('profile/layout.json', lambda d: d['rows'].insert(0, ['books']))
        self.change('profile/modules/skills.json', lambda d: d.update(enabled=False))
        output = build(self.root)
        self.assertIn('assets/generated/module-books.svg', output)
        self.assertNotIn('assets/generated/module-skills.svg', output)
        self.assertIn('书架', output['assets/generated/row-01.svg'])
        self.assertIn('width="1000.0"', output['assets/generated/module-about.svg'])

    def test_invalid_module_ids_and_duplicate_ids_fail(self):
        for rows in ([['../secret']], [['about'], ['about']]):
            self.change('profile/layout.json', lambda d: d.update(rows=rows))
            with self.assertRaises(ValueError):
                load(self.root)

    def test_unsafe_links_are_rejected(self):
        for url in ('javascript:alert(1)', 'data:text/html,x', 'https://x.test/"test', 'https://x.test/a\nb'):
            self.assertFalse(valid_url(url))
        self.assertTrue(valid_url('https://github.com/Alesia0411'))
        self.assertTrue(valid_url('mailto:example@example.com'))
        self.change('profile/modules/contact.json', lambda d: d['items'][0].update(url='javascript:alert(1)'))
        with self.assertRaises(ValueError):
            load(self.root)

    def test_mobile_is_stacked_and_links_are_clickable_html(self):
        result = build(self.root)
        desktop = ET.fromstring(result['assets/generated/row-01.svg'])
        mobile = ET.fromstring(result['assets/generated/row-01-mobile.svg'])
        self.assertGreater(float(mobile.attrib['height']), float(desktop.attrib['height']))
        self.assertIn('(max-width: 600px)', result['README.md'])
        self.assertIn('<a href="https://github.com/Alesia0411">GitHub', result['README.md'])
        self.assertIn('<details>', result['README.md'])
        self.assertNotIn('<style', result['README.md'])


if __name__ == '__main__':
    unittest.main()
