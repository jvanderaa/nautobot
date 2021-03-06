import os
import tempfile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase, TransactionTestCase

from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Manufacturer,
    Platform,
    Site,
    Region,
)
from nautobot.extras.models import ConfigContext, GitRepository, Status, Tag
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.choices import ColorChoices
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
)


class TagTest(TestCase):
    def test_create_tag_unicode(self):
        tag = Tag(name="Testing Unicode: 台灣")
        tag.save()

        self.assertEqual(tag.slug, "testing-unicode-台灣")


class ConfigContextTest(TestCase):
    """
    These test cases deal with the weighting, ordering, and deep merge logic of config context data.

    It also ensures the various config context querysets are consistent.
    """

    def setUp(self):

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        self.devicetype = DeviceType.objects.create(
            manufacturer=manufacturer, model="Device Type 1", slug="device-type-1"
        )
        self.devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        self.region = Region.objects.create(name="Region")
        self.site = Site.objects.create(name="Site-1", slug="site-1", region=self.region)
        self.platform = Platform.objects.create(name="Platform")
        self.tenantgroup = TenantGroup.objects.create(name="Tenant Group")
        self.tenant = Tenant.objects.create(name="Tenant", group=self.tenantgroup)
        self.tag = Tag.objects.create(name="Tag", slug="tag")
        self.tag2 = Tag.objects.create(name="Tag2", slug="tag2")

        self.device = Device.objects.create(
            name="Device 1",
            device_type=self.devicetype,
            device_role=self.devicerole,
            site=self.site,
        )

    def test_higher_weight_wins(self):

        ConfigContext.objects.create(name="context 1", weight=101, data={"a": 123, "b": 456, "c": 777})
        ConfigContext.objects.create(name="context 2", weight=100, data={"a": 123, "b": 456, "c": 789})

        expected_data = {"a": 123, "b": 456, "c": 777}
        self.assertEqual(self.device.get_config_context(), expected_data)

    def test_name_ordering_after_weight(self):

        ConfigContext.objects.create(name="context 1", weight=100, data={"a": 123, "b": 456, "c": 777})
        ConfigContext.objects.create(name="context 2", weight=100, data={"a": 123, "b": 456, "c": 789})

        expected_data = {"a": 123, "b": 456, "c": 789}
        self.assertEqual(self.device.get_config_context(), expected_data)

    def test_annotation_same_as_get_for_object(self):
        """
        This test incorperates features from all of the above tests cases to ensure
        the annotate_config_context_data() and get_for_object() queryset methods are the same.
        """
        ConfigContext.objects.create(name="context 1", weight=101, data={"a": 123, "b": 456, "c": 777})
        ConfigContext.objects.create(name="context 2", weight=100, data={"a": 123, "b": 456, "c": 789})
        ConfigContext.objects.create(name="context 3", weight=99, data={"d": 1})
        ConfigContext.objects.create(name="context 4", weight=99, data={"d": 2})

        annotated_queryset = Device.objects.filter(name=self.device.name).annotate_config_context_data()
        self.assertEqual(self.device.get_config_context(), annotated_queryset[0].get_config_context())

    def test_annotation_same_as_get_for_object_device_relations(self):

        site_context = ConfigContext.objects.create(name="site", weight=100, data={"site": 1})
        site_context.sites.add(self.site)
        region_context = ConfigContext.objects.create(name="region", weight=100, data={"region": 1})
        region_context.regions.add(self.region)
        platform_context = ConfigContext.objects.create(name="platform", weight=100, data={"platform": 1})
        platform_context.platforms.add(self.platform)
        tenant_group_context = ConfigContext.objects.create(name="tenant group", weight=100, data={"tenant_group": 1})
        tenant_group_context.tenant_groups.add(self.tenantgroup)
        tenant_context = ConfigContext.objects.create(name="tenant", weight=100, data={"tenant": 1})
        tenant_context.tenants.add(self.tenant)
        tag_context = ConfigContext.objects.create(name="tag", weight=100, data={"tag": 1})
        tag_context.tags.add(self.tag)

        device = Device.objects.create(
            name="Device 2",
            site=self.site,
            tenant=self.tenant,
            platform=self.platform,
            device_role=self.devicerole,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(device.get_config_context(), annotated_queryset[0].get_config_context())

    def test_annotation_same_as_get_for_object_virtualmachine_relations(self):

        site_context = ConfigContext.objects.create(name="site", weight=100, data={"site": 1})
        site_context.sites.add(self.site)
        region_context = ConfigContext.objects.create(name="region", weight=100, data={"region": 1})
        region_context.regions.add(self.region)
        platform_context = ConfigContext.objects.create(name="platform", weight=100, data={"platform": 1})
        platform_context.platforms.add(self.platform)
        tenant_group_context = ConfigContext.objects.create(name="tenant group", weight=100, data={"tenant_group": 1})
        tenant_group_context.tenant_groups.add(self.tenantgroup)
        tenant_context = ConfigContext.objects.create(name="tenant", weight=100, data={"tenant": 1})
        tenant_context.tenants.add(self.tenant)
        tag_context = ConfigContext.objects.create(name="tag", weight=100, data={"tag": 1})
        tag_context.tags.add(self.tag)
        cluster_group = ClusterGroup.objects.create(name="Cluster Group")
        cluster_group_context = ConfigContext.objects.create(
            name="cluster group", weight=100, data={"cluster_group": 1}
        )
        cluster_group_context.cluster_groups.add(cluster_group)
        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(name="Cluster", group=cluster_group, type=cluster_type)
        cluster_context = ConfigContext.objects.create(name="cluster", weight=100, data={"cluster": 1})
        cluster_context.clusters.add(cluster)

        virtual_machine = VirtualMachine.objects.create(
            name="VM 1",
            cluster=cluster,
            tenant=self.tenant,
            platform=self.platform,
            role=self.devicerole,
        )
        virtual_machine.tags.add(self.tag)

        annotated_queryset = VirtualMachine.objects.filter(name=virtual_machine.name).annotate_config_context_data()
        self.assertEqual(
            virtual_machine.get_config_context(),
            annotated_queryset[0].get_config_context(),
        )

    def test_multiple_tags_return_distinct_objects(self):
        """
        Tagged items use a generic relationship, which results in duplicate rows being returned when queried.
        This is combatted by by appending distinct() to the config context querysets. This test creates a config
        context assigned to two tags and ensures objects related by those same two tags result in only a single
        config context record being returned.

        See https://github.com/netbox-community/netbox/issues/5314
        """
        tag_context = ConfigContext.objects.create(name="tag", weight=100, data={"tag": 1})
        tag_context.tags.add(self.tag)
        tag_context.tags.add(self.tag2)

        device = Device.objects.create(
            name="Device 3",
            site=self.site,
            tenant=self.tenant,
            platform=self.platform,
            device_role=self.devicerole,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)
        device.tags.add(self.tag2)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(ConfigContext.objects.get_for_object(device).count(), 1)
        self.assertEqual(device.get_config_context(), annotated_queryset[0].get_config_context())

    def test_multiple_tags_return_distinct_objects_with_seperate_config_contexts(self):
        """
        Tagged items use a generic relationship, which results in duplicate rows being returned when queried.
        This is combatted by by appending distinct() to the config context querysets. This test creates a config
        context assigned to two tags and ensures objects related by those same two tags result in only a single
        config context record being returned.

        This test case is seperate from the above in that it deals with multiple config context objects in play.

        See https://github.com/netbox-community/netbox/issues/5387
        """
        tag_context_1 = ConfigContext.objects.create(name="tag-1", weight=100, data={"tag": 1})
        tag_context_1.tags.add(self.tag)
        tag_context_2 = ConfigContext.objects.create(name="tag-2", weight=100, data={"tag": 1})
        tag_context_2.tags.add(self.tag2)

        device = Device.objects.create(
            name="Device 3",
            site=self.site,
            tenant=self.tenant,
            platform=self.platform,
            device_role=self.devicerole,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)
        device.tags.add(self.tag2)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(ConfigContext.objects.get_for_object(device).count(), 2)
        self.assertEqual(device.get_config_context(), annotated_queryset[0].get_config_context())


class GitRepositoryTest(TransactionTestCase):
    """
    Tests for the GitRepository model class.

    Note: This is a TransactionTestCase, rather than a TestCase, because the GitRepository save() method uses
    transaction.on_commit(), which doesn't get triggered in a normal TestCase.
    """

    SAMPLE_TOKEN = "dc6542736e7b02c159d14bc08f972f9ec1e2c45fa"

    def setUp(self):
        self.repo = GitRepository(
            name="Test Git Repository",
            slug="test-git-repo",
            remote_url="http://localhost/git.git",
            username="oauth2",
        )
        self.repo.save(trigger_resync=False)

    def test_token_rendered(self):
        self.assertEqual(self.repo.token_rendered, "—")
        self.repo._token = self.SAMPLE_TOKEN
        self.assertEqual(self.repo.token_rendered, GitRepository.TOKEN_PLACEHOLDER)
        self.repo._token = ""
        self.assertEqual(self.repo.token_rendered, "—")

    def test_filesystem_path(self):
        self.assertEqual(self.repo.filesystem_path, os.path.join(settings.GIT_ROOT, self.repo.slug))

    def test_save_preserve_token(self):
        self.repo._token = self.SAMPLE_TOKEN
        self.repo.save(trigger_resync=False)
        self.assertEqual(self.repo._token, self.SAMPLE_TOKEN)
        # As if the user had submitted an "Edit" form, which displays the token placeholder instead of the actual token
        self.repo._token = GitRepository.TOKEN_PLACEHOLDER
        self.repo.save(trigger_resync=False)
        self.assertEqual(self.repo._token, self.SAMPLE_TOKEN)
        # As if the user had deleted a pre-existing token from the UI
        self.repo._token = ""
        self.repo.save(trigger_resync=False)
        self.assertEqual(self.repo._token, "")

    def test_verify_user(self):
        self.assertEqual(self.repo.username, "oauth2")

    def test_save_relocate_directory(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            with self.settings(GIT_ROOT=tmpdirname):
                initial_path = self.repo.filesystem_path
                self.assertIn(self.repo.slug, initial_path)
                os.makedirs(initial_path)

                self.repo.slug = "a-new-location"
                self.repo.save(trigger_resync=False)

                self.assertFalse(os.path.exists(initial_path))
                new_path = self.repo.filesystem_path
                self.assertIn(self.repo.slug, new_path)
                self.assertTrue(os.path.isdir(new_path))


class StatusTest(TestCase):
    """
    Tests for the `Status` model class.
    """

    def setUp(self):
        self.status = Status.objects.create(name="delete_me", slug="delete-me", color=ColorChoices.COLOR_RED)

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = DeviceRole.objects.create(name="Device Role 1")
        site = Site.objects.create(name="Site-1")

        self.device = Device.objects.create(
            name="Device 1",
            device_type=devicetype,
            device_role=devicerole,
            site=site,
            status=self.status,
        )

    def test_uniqueness(self):
        # A `delete_me` Status already exists.
        with self.assertRaises(IntegrityError):
            Status.objects.create(name="delete_me")

    def test_delete_protection(self):
        # Protected delete will fail
        with self.assertRaises(ProtectedError):
            self.status.delete()

        # Delete the device
        self.device.delete()

        # Now that it's not in use, delete will succeed.
        self.status.delete()
        self.assertEqual(self.status.pk, None)

    def test_color(self):
        self.assertEqual(self.status.color, ColorChoices.COLOR_RED)

        # Valid color
        self.status.color = ColorChoices.COLOR_PURPLE
        self.status.full_clean()

        # Invalid color
        self.status.color = "red"
        with self.assertRaises(ValidationError):
            self.status.full_clean()

    def test_name(self):
        # Test a bunch of wackado names.
        tests = [
            "CAPSLOCK",
            "---;;a;l^^^2ZSsljk¡",
            "-42",
            "392405834ioafdjskl;ajr30894fjakl;fs___π",
        ]
        for test in tests:
            self.status.name = test
            self.status.clean()
            self.status.save()
            self.assertEquals(str(self.status), test)
