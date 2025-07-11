"""
Factory classes for creating test plugin data
"""

import factory
from factory import Faker, SubFactory, LazyAttribute
from datetime import datetime, timezone
from typing import Dict, Any


class PluginFactory(factory.Factory):
    """Factory for creating plugin data."""
    
    class Meta:
        model = dict
    
    author = Faker("user_name")
    name = Faker("word")
    version = factory.Sequence(lambda n: f"0.0.{n}")
    description = Faker("sentence", nb_words=10)
    tags = factory.List([Faker("word") for _ in range(3)])
    downloads = Faker("random_int", min=0, max=10000)
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    
    @factory.post_generation
    def additional_fields(obj, create, extracted, **kwargs):
        """Add any additional fields passed as kwargs."""
        if kwargs:
            obj.update(kwargs)


class MarketplacePluginFactory(PluginFactory):
    """Factory for marketplace plugin data."""
    
    download_url = LazyAttribute(
        lambda o: f"https://marketplace.dify.ai/api/v1/plugins/{o.author}/{o.name}/{o.version}/download"
    )
    repository_url = LazyAttribute(
        lambda o: f"https://github.com/{o.author}/dify-plugin-{o.name}"
    )
    homepage = LazyAttribute(lambda o: o.repository_url)
    
    class Meta:
        model = dict


class GitHubReleaseFactory(factory.Factory):
    """Factory for GitHub release data."""
    
    class Meta:
        model = dict
    
    id = Faker("random_int", min=1000000, max=9999999)
    tag_name = factory.Sequence(lambda n: f"v0.0.{n}")
    name = LazyAttribute(lambda o: f"Release {o.tag_name}")
    draft = False
    prerelease = False
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    published_at = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    body = Faker("paragraph", nb_sentences=5)
    
    @factory.post_generation
    def assets(obj, create, extracted, **kwargs):
        """Generate release assets."""
        if not create:
            return
        
        if extracted:
            obj["assets"] = extracted
        else:
            obj["assets"] = GitHubAssetFactory.create_batch(2)


class GitHubAssetFactory(factory.Factory):
    """Factory for GitHub release asset data."""
    
    class Meta:
        model = dict
    
    id = Faker("random_int", min=1000000, max=9999999)
    name = factory.Sequence(lambda n: f"plugin_{n}.difypkg")
    label = None
    state = "uploaded"
    content_type = "application/zip"
    size = Faker("random_int", min=1000, max=1000000)
    download_count = Faker("random_int", min=0, max=1000)
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    browser_download_url = LazyAttribute(
        lambda o: f"https://github.com/owner/repo/releases/download/v1.0.0/{o.name}"
    )


class TaskFactory(factory.Factory):
    """Factory for creating task data."""
    
    class Meta:
        model = dict
    
    task_id = factory.Faker("uuid4")
    type = factory.Faker("random_element", elements=["market", "github", "local"])
    status = factory.Faker("random_element", elements=["pending", "processing", "completed", "failed"])
    progress = factory.Faker("random_int", min=0, max=100)
    message = factory.Faker("sentence", nb_words=6)
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    
    @factory.post_generation
    def parameters(obj, create, extracted, **kwargs):
        """Add task parameters based on type."""
        if not create:
            return
        
        if obj["type"] == "market":
            obj["parameters"] = {
                "author": "langgenius",
                "name": "agent",
                "version": "0.0.9",
                "platform": "manylinux2014_x86_64"
            }
        elif obj["type"] == "github":
            obj["parameters"] = {
                "repo": "owner/repo",
                "release": "v1.0.0",
                "asset": "plugin.difypkg",
                "platform": "manylinux2014_x86_64"
            }
        elif obj["type"] == "local":
            obj["parameters"] = {
                "filename": "plugin.difypkg",
                "platform": "manylinux2014_x86_64"
            }
        
        if extracted:
            obj["parameters"].update(extracted)


class WebSocketMessageFactory(factory.Factory):
    """Factory for WebSocket message data."""
    
    class Meta:
        model = dict
    
    type = factory.Faker("random_element", elements=["task_update", "heartbeat", "error", "log"])
    task_id = factory.Faker("uuid4")
    timestamp = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    
    @factory.post_generation
    def data(obj, create, extracted, **kwargs):
        """Add message data based on type."""
        if not create:
            return
        
        if obj["type"] == "task_update":
            obj["data"] = {
                "status": "processing",
                "progress": 50,
                "message": "Processing plugin..."
            }
        elif obj["type"] == "error":
            obj["data"] = {
                "error": "Something went wrong",
                "details": "Error details here"
            }
        elif obj["type"] == "log":
            obj["data"] = {
                "level": "info",
                "message": "Log message here"
            }
        
        if extracted:
            obj["data"] = extracted