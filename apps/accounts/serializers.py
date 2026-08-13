from rest_framework import serializers

from .models import LoginEvent, User
from .validators import validate_avatar_extension, validate_avatar_size


class UserSerializer(serializers.ModelSerializer):
    """Profil utilisateur — sert à /me/ et à l'historique des inscriptions."""

    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "age", "country", "role", "is_active", "date_joined", "avatar_url"]
        read_only_fields = ["id", "role", "is_active", "date_joined", "avatar_url"]

    def get_avatar_url(self, obj: User) -> str | None:
        if not obj.avatar:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        query = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("Un compte existe déjà avec cette adresse email.")
        return value


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField(validators=[validate_avatar_extension, validate_avatar_size])


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})


class RegisterSerializer(serializers.ModelSerializer):
    """Reprend exactement les champs du formulaire d'inscription du frontend
    (SignupForm.tsx) : nom complet, email, mot de passe."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    age = serializers.IntegerField(min_value=1, max_value=120)
    country = serializers.ChoiceField(choices=User.Country.choices)

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "age", "country", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cette adresse email.")
        return value

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Reprend les champs du formulaire de connexion (LoginForm.tsx) :
    email, mot de passe."""

    email = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class LoginEventSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = LoginEvent
        fields = [
            "id",
            "user",
            "user_email",
            "email_attempted",
            "success",
            "ip_address",
            "user_agent",
            "created_at",
            "logout_at",
        ]

    def get_user_email(self, obj: LoginEvent) -> str | None:
        return obj.user.email if obj.user_id else None
