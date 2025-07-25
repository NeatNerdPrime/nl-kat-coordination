from datetime import datetime, timezone
from typing import Any

import structlog
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from tools.forms.ooi import SetClearanceLevelForm
from tools.view_helpers import Breadcrumb, get_mandatory_fields, get_ooi_url

from octopoes.models import EmptyScanProfile, InheritedScanProfile
from rocky.views.ooi_detail import OOIDetailView

logger = structlog.get_logger(__name__)


class ScanProfileDetailView(FormView, OOIDetailView):
    template_name = "scan_profiles/scan_profile_detail.html"
    form_class = SetClearanceLevelForm

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        if self.ooi.scan_profile and self.ooi.scan_profile.user_id:
            try:
                context["scan_profile_user"] = get_user_model().objects.get(id=self.ooi.scan_profile.user_id)
            except get_user_model().DoesNotExist:
                pass
        return context

    def get_initial(self):
        initial = super().get_initial()

        if self.ooi.scan_profile and not isinstance(self.ooi.scan_profile, InheritedScanProfile):
            initial["level"] = self.ooi.scan_profile.level

        return initial


class ScanProfileResetView(OOIDetailView):
    template_name = "scan_profiles/scan_profile_reset.html"

    def get(self, request, *args, **kwargs):
        result = super().get(request, *args, **kwargs)
        if not self.ooi.scan_profile or self.ooi.scan_profile.scan_profile_type != "declared":
            messages.add_message(
                self.request,
                messages.WARNING,
                _("Can not reset scan level. Scan level of {ooi_name} not declared").format(
                    ooi_name=self.ooi.human_readable
                ),
            )
            return redirect(get_ooi_url("scan_profile_detail", self.ooi.primary_key, self.organization.code))

        return result

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.octopoes_api_connector.save_scan_profile(
            EmptyScanProfile(reference=self.ooi.reference), valid_time=datetime.now(timezone.utc)
        )
        logger.info("Scan profiles set to empty", event_code="800011", ooi=self.ooi.reference)

        return redirect(get_ooi_url("scan_profile_detail", self.ooi.primary_key, self.organization.code))

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "url": get_ooi_url("scan_profile_detail", self.ooi.primary_key, self.organization.code),
                "text": _("Reset"),
            }
        )
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        return context
