import os
import click
from xml.etree import ElementTree


WORKSPACE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<project>
  <component name="RunManager">
    <configuration name="debug" type="PythonConfigurationType" factoryName="Python" temporary="true">
      <option name="INTERPRETER_OPTIONS" value="" />
      <option name="PARENT_ENVS" value="true" />
      <envs>
        <env name="PYTHONUNBUFFERED" value="1" />
      </envs>
      <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$/deploy" />
      <option name="IS_MODULE_SDK" value="false" />
      <option name="ADD_CONTENT_ROOTS" value="true" />
      <option name="ADD_SOURCE_ROOTS" value="true" />
      <module name="{0}" />
      <EXTENSION ID="PythonCoverageRunConfigurationExtension" enabled="false"
       sample_coverage="true" runner="coverage.py" />
      <option name="SCRIPT_NAME" value="$PROJECT_DIR$/deploy/run.py" />
      <option name="PARAMETERS" value="debug" />
      <option name="SHOW_COMMAND_LINE" value="false" />
      <option name="EMULATE_TERMINAL" value="false" />
      <option name="MODULE_MODE" value="false" />
    </configuration>
    <configuration name="deploy_sh" type="PythonConfigurationType" factoryName="Python" temporary="true">
      <option name="INTERPRETER_OPTIONS" value="" />
      <option name="PARENT_ENVS" value="true" />
      <envs>
        <env name="PYTHONUNBUFFERED" value="1" />
      </envs>
      <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$/deploy" />
      <option name="IS_MODULE_SDK" value="false" />
      <option name="ADD_CONTENT_ROOTS" value="true" />
      <option name="ADD_SOURCE_ROOTS" value="true" />
      <module name="{0}" />
      <EXTENSION ID="PythonCoverageRunConfigurationExtension" enabled="false"
       sample_coverage="true" runner="coverage.py" />
      <option name="SCRIPT_NAME" value="$PROJECT_DIR$/deploy/run.py" />
      <option name="PARAMETERS" value="build_deploy_sh" />
      <option name="SHOW_COMMAND_LINE" value="false" />
      <option name="EMULATE_TERMINAL" value="false" />
      <option name="MODULE_MODE" value="false" />
    </configuration>
  </component>
</project>"""


IML_FILE_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<module type="PYTHON_MODULE" version="4">
  <component name="NewModuleRootManager">
    <content url="file://$MODULE_DIR$">
      <sourceFolder url="file://$MODULE_DIR$/{0}/.parasite" isTestSource="false" />
    </content>
    <orderEntry type="inheritedJdk" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
  <component name="TestRunnerService">
    <option name="projectConfiguration" value="py.test" />
    <option name="PROJECT_TEST_RUNNER" value="py.test" />
  </component>
</module>"""


def create_temp_project(project_path, project_name):
    idea_path = os.path.join(project_path, '.idea')
    if not os.path.exists(idea_path):
        os.makedirs(idea_path)

    workspace_xml = WORKSPACE_XML.format(project_name)
    with open(os.path.join(idea_path, 'workspace.xml'), 'w') as f:
        f.write(workspace_xml)


def add_parasite_path_inspector(project_path, project_name):
    idea_path = os.path.join(project_path, '.idea')
    if not os.path.exists(idea_path):
        os.makedirs(idea_path)

    iml_file_name = os.path.join(idea_path, '{0}.iml'.format(project_name))
    if not os.path.exists(iml_file_name):
        iml = IML_FILE_CONTENT.format(project_name)
        with open(iml_file_name, 'w') as f:
            f.write(iml)

    try:
        tree = ElementTree.ElementTree(file=iml_file_name)
        parasite_url = 'file://$MODULE_DIR$/{0}/.parasite'.format(project_name)
        xml_edited = False
        already_added = False
        module_namager_e = None

        for e in tree.iterfind('./component[@name="NewModuleRootManager"]'):
            module_namager_e = e
            if already_added:
                break

            for content_e in e.getchildren():
                if already_added:
                    break

                if content_e.tag != 'content' or 'url' not in content_e.attrib:
                    continue
                if content_e.attrib['url'] == 'file://$MODULE_DIR$':
                    for source_e in content_e.getchildren():
                        if source_e.tag == 'sourceFolder' and \
                                'url' in source_e.attrib and \
                                source_e.attrib['url'] == parasite_url:
                            already_added = True
                            break
                    if not already_added:
                        content_e.append(ElementTree.Element('sourceFolder', {'url': parasite_url}))
                        xml_edited = True
                        already_added = True
                        break
                elif content_e.attrib['url'] == parasite_url:
                    already_added = True
                    break

        if module_namager_e is not None and not already_added:
            module_namager_e.append(ElementTree.Element('content', {'url': parasite_url}))
            xml_edited = True

        if xml_edited:
            tree.write(iml_file_name)

    except Exception as e:
        str(e)


def ignore_parasite(project_path, project_name):
    ignore_file = os.path.join(project_path, '.gitignore')
    parasite_path = os.path.join(project_path, project_name, '.parasite').lower()
    if not os.path.exists(ignore_file):
        return

    with open(ignore_file) as f:
        ignore_items = f.readlines()

    for ignore_item in ignore_items:
        ignore_item = os.path.join(os.path.relpath(project_path, os.getcwd()), ignore_item.strip())
        if os.path.realpath(ignore_item).lower() == parasite_path:
            return

    if not click.confirm('是否将调试用的 .parasite 文件夹添加到 git 忽略项中？', default=True):
        return

    ignore_items.append(os.path.relpath(parasite_path, project_path.lower()))
    with open(ignore_file, 'w') as f:
        f.writelines(ignore_items)
