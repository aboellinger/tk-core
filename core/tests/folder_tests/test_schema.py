"""
Copyright (c) 2012 Shotgun Software, Inc
"""
import os
import unittest
import shutil
from mock import Mock
import tank
from tank_vendor import yaml
from tank.folder import Schema
from tank import TankError
from tank import hook
from tank import folder
from tank_test.tank_test_base import *


class TestSchemaCreateFolders(TankTestBase):
    def setUp(self):
        """Sets up entities in mocked shotgun database and creates Mock objects
        to pass in as callbacks to Schema.create_folders. The mock objects are
        then queried to see what paths the code attempted to create.
        """
        super(TestSchemaCreateFolders, self).setUp()
        self.setup_fixtures()
        self.seq = {"type": "Sequence",
                    "id": 2,
                    "code": "seq_code",
                    "project": self.project}
        self.shot = {"type": "Shot",
                     "id": 1,
                     "code": "shot_code",
                     "sg_sequence": self.seq,
                     "project": self.project}
        self.step = {"type": "Step",
                     "id": 3,
                     "code": "step_code",
                     "short_name": "step_short_name"}
        self.asset = {"type": "Asset",
                    "id": 4,
                    "sg_asset_type": "assettype",
                    "code": "assetname",
                    "project": self.project}
        self.humanuser = {"type": "HumanUser",
                          "id": 3,
                          "login": "login_name"}
        self.task = {"type": "Task",
                     "id": 23,
                     "task_assignees": [self.humanuser],
                     "entity": self.shot,
                     "step": self.step,
                     "project": self.project}

        entities = [self.shot, self.seq, self.step, self.project, self.asset, self.humanuser, self.task]

        # Add these to mocked shotgun
        self.add_to_sg_mock_db(entities)

        self.tk = tank.Tank(self.project_root)

        # add mock schema data so that a list of the asset type enum values can be returned
        data = {}
        data["properties"] = {}
        data["properties"]["valid_values"] = {}
        data["properties"]["valid_values"]["value"] = ["assettype"]
        self.add_to_sg_schema_db("Asset", "sg_asset_type", data)

        # Mock rather than writing to disk
        self.mock_make_folder = Mock()
        self.mock_copy_file = Mock()

        self.schema_location = os.path.join(self.project_root, "tank", "config", "core", "schema")


    def test_shot(self):
        """Tests paths used in making a shot are as expected."""
        expected_paths = self._construct_shot_paths()
        schema = Schema(self.tk, 
                        self.schema_location, 
                        self.mock_make_folder, 
                        self.mock_copy_file,
                        preview=False)
        schema.create_folders("Shot", self.shot["id"])
        self.assert_paths_to_create(expected_paths)

    def test_white_space(self):
        # make illegal value
        self.shot["code"] = "name with spaces"
        self.add_to_sg_mock_db(self.shot)
        expected_paths = self._construct_shot_paths(shot_name="name-with-spaces")
        schema = Schema(self.tk, 
                        self.schema_location, 
                        self.mock_make_folder, 
                        self.mock_copy_file,
                        preview=False)
        
        schema.create_folders("Shot", self.shot["id"])
        self.assert_paths_to_create(expected_paths)

    def test_illegal_chars(self):
        illegal_chars = ["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
                         "+", "=", ":", ";", "'", "\"", "<", ">", "/", "?", 
                         "|", "/", "\\"]
        for illegal_char in illegal_chars:
            self.shot["code"] = "shot%sname" % illegal_char
            self.add_to_sg_mock_db(self.shot)
            expected_paths = self._construct_shot_paths(shot_name="shot-name")
            schema = Schema(self.tk, 
                            self.schema_location, 
                            self.mock_make_folder, 
                            self.mock_copy_file,
                            preview=False)
            
            schema.create_folders("Shot", self.shot["id"])
            self.assert_paths_to_create(expected_paths)

    def test_asset(self):
        """Tests paths used in making a asset are as expected."""
        # expected paths here are based on sg_standard start-config
        # define paths we expect for entities
        asset_type_path = os.path.join(self.project_root, "assets", self.asset["sg_asset_type"])
        
        asset_path = os.path.join(asset_type_path, self.asset["code"])
        
        step_path = os.path.join(asset_path, self.step["short_name"])
        
        expected_paths = [asset_type_path, asset_path, step_path]
        
        # add non-entity paths
        expected_paths.append(os.path.join(step_path, "publish"))
        expected_paths.append(os.path.join(step_path, "images"))
        expected_paths.append(os.path.join(step_path, "review"))
        expected_paths.append(os.path.join(step_path, "work"))
        expected_paths.append(os.path.join(step_path, "work", "snapshots"))
        expected_paths.append(os.path.join(step_path, "out"))

        self.tk = tank.Tank(self.project_root)

        schema = Schema(self.tk, 
                        self.schema_location, 
                        self.mock_make_folder, 
                        self.mock_copy_file,
                        preview=False)
        
        schema.create_folders("Asset", self.asset["id"])
        self.assert_paths_to_create(expected_paths)
    
    def test_scene(self):
        """Tests folder creation works with Step higher up the hierarchy than normal"""
        
        scene = {
            "type": "Scene",
            "id": 5,
            "code": "scenename",
            "project": self.project
        }
        
        extra_step = {
            "type": "Step",
            "id": 6,
            "code": "step_code",
            "short_name": "extra_short_name"
        }
        
        self.add_to_sg_mock_db([scene, extra_step])
        
        expected_paths = []
        expected_paths.append(os.path.join(self.project_root, "scenes"))
        expected_paths.append(os.path.join(self.project_root, "scenes", "step_short_name"))
        expected_paths.append(os.path.join(self.project_root, "scenes", "step_short_name", "scenename"))
        expected_paths.append(os.path.join(self.project_root, "scenes", "step_short_name", "scenename", "work"))
        expected_paths.append(os.path.join(self.project_root, "scenes", "extra_short_name"))
        expected_paths.append(os.path.join(self.project_root, "scenes", "extra_short_name", "scenename"))
        expected_paths.append(os.path.join(self.project_root, "scenes", "extra_short_name", "scenename", "work"))
        
        schema = Schema(self.tk, 
                        self.schema_location, 
                        self.mock_make_folder, 
                        self.mock_copy_file,
                        preview=False)
        
        schema.create_folders("Scene", scene["id"])
        self.assert_paths_to_create(expected_paths)

    def test_project(self):
        """Tests paths used in making a project are as expected."""
        # paths based on sg_standard starter config
        expected_paths = []
        expected_paths.append(os.path.join(self.project_root, "sequences"))
        expected_paths.append(os.path.join(self.project_root, "scenes"))
        expected_paths.append(os.path.join(self.project_root, "assets"))
        expected_paths.append(os.path.join(self.project_root, "assets", self.asset["sg_asset_type"]))
        expected_paths.append(os.path.join(self.project_root, "reference"))
        expected_paths.append(os.path.join(self.project_root, "reference", "artwork"))
        expected_paths.append(os.path.join(self.project_root, "reference", "footage"))

        schema = Schema(self.tk, 
                        self.schema_location, 
                        self.mock_make_folder, 
                        self.mock_copy_file,
                        preview=False)
        
        schema.create_folders("Project", self.project["id"])
        self.assert_paths_to_create(expected_paths)

    def _construct_shot_paths(self, sequence_name=None, shot_name=None, step_name=None):
        """
        Constructs expected paths for a shot based on the sg_standard standard config.

        :param sequence_name: Override for the name of the sequence directory.
        :param shot_name: Override for the name of the shot directory.
        :param step_name: Override for the name of the step directory.

        :returns: List of paths
        """
        # expected paths here are based on sg_standard start-config
        # define paths we expect for entities
        if not sequence_name:
            sequence_name = self.seq["code"]

        sequence_path = os.path.join(self.project_root, "sequences", sequence_name)
        if not shot_name:
            shot_name = self.shot["code"]
        shot_path = os.path.join(sequence_path, shot_name)

        step_path = os.path.join(shot_path, self.step["short_name"])
        user_path = os.path.join(step_path, self.humanuser["login"])
        expected_paths = [sequence_path, shot_path, step_path, user_path]
        # add non-entity paths
        expected_paths.append(os.path.join(user_path, "publish"))
        expected_paths.append(os.path.join(user_path, "images"))
        expected_paths.append(os.path.join(user_path, "review"))
        expected_paths.append(os.path.join(user_path, "work"))
        expected_paths.append(os.path.join(user_path, "work", "snapshots"))
        expected_paths.append(os.path.join(user_path, "work", "workspace.mel"))
        expected_paths.append(os.path.join(user_path, "out"))
        return expected_paths

    def test_project_missing(self):
        """Case that project directory is missing from schema"""
        project_schema = os.path.join(self.project_root, "tank", "config", "core", "schema", "project")
        shutil.rmtree(project_schema)
        with self.assertRaises(tank.TankError):
            schema = Schema(self.tk,
                            self.schema_location, 
                            self.mock_make_folder, 
                            self.mock_copy_file,
                            preview=False)
            schema.create_folders("Project", self.project["id"])


    def assert_paths_to_create(self, expected_paths):
        """
        No file system operations are performed.
        """
        # Check paths sent to make_folder
        actual_paths = [x[0][0] for x in self.mock_make_folder.call_args_list]
        actual_paths += [x[0][1] for x in self.mock_copy_file.call_args_list]
        for expected_path in expected_paths:
            if expected_path not in actual_paths:
                assert False, "\n%s\nnot found in: [\n%s]" % (expected_path, "\n".join(actual_paths))
        for actual_path in actual_paths:
            if not any(x.startswith(actual_path) for x in expected_paths):
                assert False, "Unexpected path slated for creation: %s" % actual_path

                                
class TestSchemaCreateFoldersMultiRoot(TankTestBase):
    """Test paths generated by Schema.create folders for multi-root project."""
    def setUp(self):
        """Sets up entities in mocked shotgun database and creates Mock objects
        to pass in as callbacks to Schema.create_folders. The mock objects are
        then queried to see what paths the code attempted to create.
        """
        super(TestSchemaCreateFoldersMultiRoot, self).setUp()
        self.setup_multi_root_fixtures()
        self.seq = {"type": "Sequence",
                    "id": 2,
                    "code": "seq_code",
                    "project": self.project}
        self.shot = {"type": "Shot",
                     "id": 1,
                     "code": "shot_code",
                     "sg_sequence": self.seq,
                     "project": self.project}
        self.step = {"type": "Step",
                     "id": 3,
                     "code": "step_code",
                     "short_name": "step_short_name"}
        self.asset = {"type": "Asset",
                    "id": 4,
                    "sg_asset_type": "assettype",
                    "code": "assetname",
                    "project": self.project}

        # Add these to mocked shotgun
        self.add_to_sg_mock_db([self.shot, self.seq, self.step, self.project, self.asset])

        self.tk = tank.Tank(self.project_root)

        # Mock rather than writing to disk
        self.mock_make_folder = Mock()
        self.mock_copy_file = Mock()

        self.schema_location = os.path.join(self.project_root, "tank", "config", "core", "schema")


    def test_shot(self):
        """Tests paths used in making a shot are as expected."""
        expected_paths = self._construct_shot_paths()
        schema = Schema(self.tk, 
                        self.schema_location, 
                        self.mock_make_folder, 
                        self.mock_copy_file,
                        preview=False)
        schema.create_folders("Shot", self.shot["id"])
        self.assert_paths_to_create(expected_paths)

    def test_asset(self):
        """Tests paths used in making a asset are as expected."""
        # expected paths here are based on sg_standard start-config
        # define paths we expect for entities
        asset_folder_name = "%s_%s" % (self.asset["sg_asset_type"], self.asset["code"])
        asset_path = os.path.join(self.alt_root_1, "assets", asset_folder_name)
        step_path = os.path.join(asset_path, self.step["short_name"])
        expected_paths = [asset_path, step_path]
        # config path
        expected_paths.append(os.path.join(self.alt_root_1, "tank", "config"))
        # add non-entity paths
        expected_paths.append(os.path.join(step_path, "publish"))
        expected_paths.append(os.path.join(step_path, "images"))
        expected_paths.append(os.path.join(step_path, "review"))
        expected_paths.append(os.path.join(step_path, "work"))
        expected_paths.append(os.path.join(step_path, "work", "snapshots"))
        expected_paths.append(os.path.join(step_path, "out"))

        schema = Schema(self.tk, 
                        self.schema_location, 
                        self.mock_make_folder, 
                        self.mock_copy_file,
                        preview=False)
        schema.create_folders("Asset", self.asset["id"])
        self.assert_paths_to_create(expected_paths)

    def test_project(self):
        """
        Tests paths used in making a project are as expected when single project directory
        with no yaml file exits.
        """
        # paths based on sg_standard starter config modified to be multi-project
        expected_paths = []
        expected_paths.append(os.path.join(self.project_root, "sequences"))
        expected_paths.append(os.path.join(self.project_root, "reference"))
        expected_paths.append(os.path.join(self.project_root, "reference", "artwork"))
        expected_paths.append(os.path.join(self.project_root, "reference", "footage"))

        expected_paths.append(os.path.join(self.alt_root_1, "tank"))
        expected_paths.append(os.path.join(self.alt_root_1, "tank", "config"))
        expected_paths.append(os.path.join(self.alt_root_1, "assets"))
        expected_paths.append(os.path.join(self.alt_root_1, "alternate_reference"))
        schema = Schema(self.tk, 
                        self.schema_location, 
                        self.mock_make_folder, 
                        self.mock_copy_file,
                        preview=False)
        schema.create_folders("Project", self.project["id"])
        self.assert_paths_to_create(expected_paths)


    def test_primary_project_file(self):
        """
        Test that file with primary project path is written in the tank config area of 
        an alternative project path.
        """
        def make_folder(path, entity):
            if not os.path.exists(path):
                old_umask = os.umask(0)
                os.makedirs(path, 0777)
                os.umask(old_umask)
        
        schema = Schema(self.tk, 
                        self.schema_location, 
                        make_folder, 
                        self.mock_copy_file,
                        preview=False)
        schema.create_folders("Project", self.project["id"])
        primary_file_path = os.path.join(self.alt_root_1, "tank", "config", "primary_project.yml")
        self.assertTrue(os.path.exists(primary_file_path))

        # test contents
        expected = {"windows_path": self.project_root,
                    "linux_path":self.project_root,
                    "mac_path":self.project_root}

        with open(primary_file_path, "r") as open_file:
            data = yaml.load(open_file)
        self.assertEqual(expected, data)


    def test_project_one_yml_missing(self):
        """
        Case that there are mutiple projects, one non-primary without yaml a file
        """
        project_yml = os.path.join(self.schema_location, "alternate_1.yml")
        os.remove(project_yml)
        with self.assertRaises(tank.TankError):
            schema = Schema(self.tk, 
                            self.schema_location, 
                            self.mock_make_folder, 
                            self.mock_copy_file,
                            preview=False)
            schema.create_folders("Project", self.project["id"])

    def test_project_root_mismatch(self):
        """
        Case that root name specified in projects yml file does not exist in roots file.
        """
        # remove root name from the roots file
        project_name = os.path.basename(self.project_root)
        roots_path = tank.constants.get_roots_file_location(self.project_root)        
        with open(roots_path, "r") as roots_file:
            roots = yaml.load(roots_file)
        del(roots["alternate_1"])

        with open(roots_path, "w") as roots_file:
            roots_file.write(yaml.dump(roots))

        with self.assertRaises(tank.TankError):
            schema = Schema(self.tk, 
                            self.schema_location, 
                            self.mock_make_folder, 
                            self.mock_copy_file,
                            preview=False)
            schema.create_folders("Project", self.project["id"])

    def _construct_shot_paths(self, sequence_name=None, shot_name=None, step_name=None):
        """
        Constructs expected paths for a shot based on the multi root test schema

        :param sequence_name: Override for the name of the sequence directory.
        :param shot_name: Override for the name of the shot directory.
        :param step_name: Override for the name of the step directory.

        :returns: List of paths
        """
        # expected paths here are based on sg_standard start-config
        # define paths we expect for entities
        if not sequence_name:
            sequence_name = self.seq["code"]

        sequence_path = os.path.join(self.project_root, "sequences", sequence_name)
        if not shot_name:
            shot_name = self.shot["code"]
        shot_path = os.path.join(sequence_path, shot_name)

        step_path = os.path.join(shot_path, self.step["short_name"])
        expected_paths = [sequence_path, shot_path, step_path]
        # add non-entity paths
        expected_paths.append(os.path.join(step_path, "publish"))
        expected_paths.append(os.path.join(step_path, "images"))
        expected_paths.append(os.path.join(step_path, "review"))
        expected_paths.append(os.path.join(step_path, "work"))
        expected_paths.append(os.path.join(step_path, "work", "snapshots"))
        expected_paths.append(os.path.join(step_path, "out"))
        return expected_paths

    def assert_paths_to_create(self, expected_paths):
        """
        No file system operations are performed.
        """
        # Check paths sent to make_folder
        actual_paths = [x[0][0] for x in self.mock_make_folder.call_args_list]
        for expected_path in expected_paths:
            if expected_path not in actual_paths:
                assert False, "\n%s\nnot found in: [\n%s]" % (expected_path, "\n".join(actual_paths))
        for actual_path in actual_paths:
            if not any(x.startswith(actual_path) for x in expected_paths):
                assert False, "Unexpected path slated for creation: %s" % actual_path

class TestCreateFilesystemStructure(TankTestBase):
    """Tests of the function schema.create_folders."""
    def setUp(self):
        super(TestCreateFilesystemStructure, self).setUp()
        self.setup_fixtures()
        
        self.tk = tank.Tank(self.project_root)
        
        self.seq = {"type": "Sequence",
                    "id": 2,
                    "code": "seq_code",
                    "project": self.project}
        self.shot = {"type": "Shot",
                     "id": 1,
                     "code": "shot_code",
                     "sg_sequence": self.seq,
                     "project": self.project}
        self.step = {"type": "Step",
                     "id": 3,
                     "code": "step_code",
                     "short_name": "step_short_name"}
        self.asset = {"type": "Asset",
                    "id": 4,
                    "sg_asset_type": "assettype",
                    "code": "assetname",
                    "project": self.project}
        self.task = {"type":"Task",
                     "id": 1,
                     "content": "this task",
                     "entity": self.shot,
                     "project": self.project}

        # Add these to mocked shotgun
        self.add_to_sg_mock_db([self.shot, self.seq, self.step, self.project, self.asset, self.task])
        
        self.tk = tank.Tank(self.project_root)
        
        # add mock schema data so that a list of the asset type enum values can be returned
        data = {}
        data["properties"] = {}
        data["properties"]["valid_values"] = {}
        data["properties"]["valid_values"]["value"] = ["assettype"]
        self.add_to_sg_schema_db("Asset", "sg_asset_type", data)


    def test_create_task(self):
        # Task should create folders for it's entity
        expected = os.path.join(self.project_root, "sequences", self.seq["code"], self.shot["code"])
        self.assertFalse(os.path.exists(expected))
        folder.process_filesystem_structure(self.tk, 
                                            self.task["type"], 
                                            self.task["id"], 
                                            preview=False)
        self.assertTrue(os.path.exists(expected))

    def test_create_shot(self):
        expected = os.path.join(self.project_root, "sequences", self.seq["code"], self.shot["code"])
        self.assertFalse(os.path.exists(expected))
        folder.process_filesystem_structure(self.tk, 
                                            self.shot["type"], 
                                            self.shot["id"], 
                                            preview=False)        
        self.assertTrue(os.path.exists(expected))

    def test_create_asset(self):
        expected = os.path.join(self.project_root, "assets", self.asset["sg_asset_type"], self.asset["code"])
        self.assertFalse(os.path.exists(expected))
        folder.process_filesystem_structure(self.tk, 
                                            self.asset["type"], 
                                            self.asset["id"], 
                                            preview=False)
        self.assertTrue(os.path.exists(expected))

    def test_create_project(self):
        # Check static folders without entity children are created
        expected = os.path.join(self.project_root, "reference", "artwork")
        self.assertFalse(os.path.exists(expected))
        folder.process_filesystem_structure(self.tk, 
                                            self.project["type"], 
                                            self.project["id"], 
                                            preview=False)
        self.assertTrue(os.path.exists(expected))

    def test_create_sequence(self):
        expected = os.path.join(self.project_root, "sequences", self.seq["code"])
        self.assertFalse(os.path.exists(expected))
        folder.process_filesystem_structure(self.tk, 
                                            self.seq["type"], 
                                            self.seq["id"], 
                                            preview=False)
        self.assertTrue(os.path.exists(expected))

              
    def test_wrong_type_entity_ids(self):
        """Test passing in type other than list, int or tuple as value for entity_ids parameter.
        """
        for bad_entity_ids in ["abab", self.shot, object()]:
            with self.assertRaises(ValueError):
                folder.process_filesystem_structure(self.tk,
                                                    self.shot["type"],
                                                    bad_entity_ids,
                                                    preview=False)
              
              
              
