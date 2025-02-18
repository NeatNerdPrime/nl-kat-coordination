from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from pytest_django.asserts import assertContains, assertNotContains
from rocky.views.organization_settings import OrganizationSettingsView

from rocky.views.indemnification_add import IndemnificationAddView
from rocky.views.organization_edit import OrganizationEditView
from rocky.views.organization_list import OrganizationListView
from rocky.views.organization_member_list import OrganizationMemberListView
from tests.conftest import setup_request, create_member
from tools.models import Organization

AMOUNT_OF_TEST_ORGANIZATIONS = 50


@pytest.fixture
def bulk_organizations(active_member, blocked_member):
    with patch("katalogus.client.KATalogusClientV1"), patch("tools.models.OctopoesAPIConnector"):
        organizations = []
        for i in range(1, AMOUNT_OF_TEST_ORGANIZATIONS):
            org = Organization.objects.create(name=f"Test Organization {i}", code=f"test{i}", tags=f"test-tag{i}")

            for member in [active_member, blocked_member]:
                create_member(member.user, org)
            organizations.append(org)
    return organizations


def test_organization_list_non_superuser(rf, client_member):
    client_member.user.user_permissions.add(Permission.objects.get(codename="view_organization"))

    request = setup_request(rf.get("organization_list"), client_member.user)
    response = OrganizationListView.as_view()(request)

    assertContains(response, "Organizations")
    assertNotContains(response, "Add new organization")
    assertContains(response, client_member.organization.name)


def test_edit_organization(rf, superuser_member):
    request = setup_request(rf.get("organization_edit"), superuser_member.user)
    response = OrganizationEditView.as_view()(request, organization_code=superuser_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "Name")
    assertContains(response, "Code")
    assertContains(response, superuser_member.organization.code)
    assertContains(response, superuser_member.organization.name)
    assertContains(response, "Save organization")


def test_organization_list(rf, superuser_member, bulk_organizations, django_assert_max_num_queries):
    """Verify that this view does not query the database for each organization."""

    with django_assert_max_num_queries(
        AMOUNT_OF_TEST_ORGANIZATIONS, info="Too many queries for organization list view"
    ):
        request = setup_request(rf.get("organization_list"), superuser_member.user)
        response = OrganizationListView.as_view()(request)

        assertContains(response, "Organizations")
        assertContains(response, "Add new organization")
        assertContains(response, superuser_member.organization.name)

        for org in bulk_organizations:
            assertContains(response, org.name)


def test_organization_member_list(rf, admin_member):
    request = setup_request(rf.get("organization_member_list"), admin_member.user)
    response = OrganizationMemberListView.as_view()(request, organization_code=admin_member.organization.code)

    assertContains(response, "Organization")
    assertContains(response, admin_member.organization.name)
    assertContains(response, "Members")
    assertContains(response, "Add new member")
    assertContains(response, "Name")
    assertContains(response, admin_member.user.full_name)
    assertContains(response, "E-mail")
    assertContains(response, admin_member.user.email)
    assertContains(response, "Role")
    assertContains(response, "Admin")
    assertContains(response, "Status")
    assertContains(response, admin_member.status)
    assertContains(response, "Added")
    assertContains(response, admin_member.user.date_joined.strftime("%m/%d/%Y"))
    assertContains(response, "Assigned clearance level")
    assertContains(response, admin_member.trusted_clearance_level)
    assertContains(response, "Agreed clearance level")
    assertContains(response, admin_member.acknowledged_clearance_level)
    assertContains(response, "Edit")
    assertContains(response, admin_member.id)
    assertContains(response, "Blocked")


def test_organization_filtered_member_list(rf, superuser_member, new_member, blocked_member):
    request = setup_request(rf.get("organization_member_list", {"client_status": "blocked"}), superuser_member.user)
    response = OrganizationMemberListView.as_view()(request, organization_code=superuser_member.organization.code)

    assertNotContains(response, new_member.user.full_name)
    assertContains(response, blocked_member.user.full_name)
    assertContains(response, 'class="blocked"')
    assertNotContains(response, "New")
    assertNotContains(response, "Active")

    request2 = setup_request(rf.get("organization_member_list", {"client_status": "new"}), superuser_member.user)
    response2 = OrganizationMemberListView.as_view()(request2, organization_code=superuser_member.organization.code)

    assertContains(response2, new_member.user.full_name)
    assertNotContains(response2, blocked_member.user.full_name)
    assertContains(response2, "New")
    assertNotContains(response2, 'class="blocked"')
    assertNotContains(response2, "Active")

    request3 = setup_request(
        rf.get("organization_member_list", {"client_status": ["new", "active", "blocked"]}), superuser_member.user
    )
    response3 = OrganizationMemberListView.as_view()(request3, organization_code=superuser_member.organization.code)

    assertContains(response3, superuser_member.user.full_name)
    assertContains(response3, new_member.user.full_name)
    assertContains(response3, blocked_member.user.full_name)
    assertContains(response3, "New")
    assertContains(response3, 'class="blocked"')
    assertContains(response3, "Active")


def test_organization_does_not_exist(client, client_member):
    client.force_login(client_member.user)
    response = client.get(reverse("organization_settings", kwargs={"organization_code": "nonexistent"}))

    assert response.status_code == 404


def test_organization_no_member(client, clientuser, organization):
    client.force_login(clientuser)
    response = client.get(reverse("organization_settings", kwargs={"organization_code": organization.code}))

    assert response.status_code == 404


def test_organization_active_member(rf, active_member):
    request = setup_request(rf.get("organization_settings"), active_member.user)
    response = OrganizationSettingsView.as_view()(request, organization_code=active_member.organization.code)

    assert response.status_code == 200


def test_organization_blocked_member(rf, blocked_member):
    request = setup_request(rf.get("organization_settings"), blocked_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationSettingsView.as_view()(request, organization_code=blocked_member.organization.code)


def test_edit_organization_permissions(rf, redteam_member, client_member):
    """Redteamers and clients cannot edit organization."""
    request_redteam = setup_request(rf.get("organization_edit"), redteam_member.user)
    request_client = setup_request(rf.get("organization_edit"), client_member.user)

    with pytest.raises(PermissionDenied):
        OrganizationEditView.as_view()(request_redteam, organization_code=redteam_member.organization.code)

    with pytest.raises(PermissionDenied):
        OrganizationEditView.as_view()(
            request_client, organization_code=client_member.organization.code, pk=client_member.organization.id
        )


def test_edit_organization_indemnification(rf, redteam_member, client_member):
    """Redteamers and clients cannot add idemnification."""
    request_redteam = setup_request(rf.get("indemnification_add"), redteam_member.user)
    request_client = setup_request(rf.get("indemnification_add"), client_member.user)

    with pytest.raises(PermissionDenied):
        IndemnificationAddView.as_view()(request_redteam, organization_code=redteam_member.organization.code)

    with pytest.raises(PermissionDenied):
        IndemnificationAddView.as_view()(
            request_client, organization_code=client_member.organization.code, pk=client_member.organization.id
        )


def test_admin_rights_edits_organization(rf, admin_member):
    """Can admin edit organization?"""
    request = setup_request(rf.get("organization_edit"), admin_member.user)
    response = OrganizationEditView.as_view()(
        request, organization_code=admin_member.organization.code, pk=admin_member.organization.id
    )

    assert response.status_code == 200


def test_admin_edits_organization(rf, admin_member, mocker):
    """Admin editing organization values"""
    request = setup_request(
        rf.post(
            "organization_edit",
            {"name": "This organization name has been edited", "tags": "tag1,tag2"},
        ),
        admin_member.user,
    )
    mocker.patch("katalogus.client.KATalogusClientV1")
    mocker.patch("tools.models.OctopoesAPIConnector")
    response = OrganizationEditView.as_view()(
        request, organization_code=admin_member.organization.code, pk=admin_member.organization.id
    )

    # success post redirects to organization detail page
    assert response.status_code == 302
    assert response.url == f"/en/{admin_member.organization.code}/settings"
    resulted_request = setup_request(rf.get(response.url), admin_member.user)
    resulted_response = OrganizationSettingsView.as_view()(
        resulted_request, organization_code=admin_member.organization.code
    )
    assert resulted_response.status_code == 200

    assertContains(resulted_response, "Tags")
    assertContains(resulted_response, "tags-color-1-light plain")  # default color
    assertContains(resulted_response, "tag1")
    assertContains(resulted_response, "tag2")
