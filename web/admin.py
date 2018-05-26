from django.contrib import admin
from django.contrib.auth import get_user_model

# Register your models here.
from .models import UserSetting
from .models import Channel
from .models import ChannelSource
from .models import Upcoming
from .models import GlobalExcludeFilter
from .models import ChannelExcludeFilter
from .models import ChannelIncludeFilter


admin.site.register(UserSetting)
admin.site.register(Channel)
admin.site.register(ChannelSource)
admin.site.register(Upcoming)
admin.site.register(GlobalExcludeFilter)
admin.site.register(ChannelExcludeFilter)
admin.site.register(ChannelIncludeFilter)
