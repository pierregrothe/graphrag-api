# Release Notes Template

## 🚀 {ENV_NAME} Release v{VERSION}

### Version Information
- **Version**: {VERSION}
- **Date**: {DATE}
- **Type**: {ENV_NAME} ({ENV_TYPE})
- **Build**: {BUILD_NUMBER}

### ✨ Highlights
<!-- Add 2-3 key highlights of this release -->
-
-
-

### 🔄 What's New
<!-- List new features -->
-

### 🐛 Bug Fixes
<!-- List bug fixes -->
-

### 📈 Improvements
<!-- List improvements and optimizations -->
-

### 🔧 Technical Changes
<!-- List technical/internal changes -->
-

### 🐳 Docker Images

Pull this release:
```bash
docker pull ghcr.io/pierregrothe/graphrag-api:{VERSION}
```

Latest {ENV_NAME} image:
```bash
docker pull ghcr.io/pierregrothe/graphrag-api:{LATEST_TAG}
```

### 📦 Quick Start

#### Using Docker Run:
```bash
docker run -d \
  --name graphrag-api \
  -p 8001:8001 \
  -e JWT_SECRET_KEY="change-this-in-production" \
  -e LLM_PROVIDER="ollama" \
  -e OLLAMA_BASE_URL="http://host.docker.internal:11434" \
  ghcr.io/pierregrothe/graphrag-api:{VERSION}
```

#### Using Docker Compose:
```yaml
services:
  graphrag-api:
    image: ghcr.io/pierregrothe/graphrag-api:{VERSION}
    container_name: graphrag-api
    ports:
      - "8001:8001"
    environment:
      - JWT_SECRET_KEY=change-this-in-production
      - LLM_PROVIDER=ollama
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - ./data:/app/data
      - ./workspaces:/app/workspaces
```

### 🔗 Links
- [Docker Image](https://github.com/pierregrothe/graphrag-api/pkgs/container/graphrag-api)
- [Documentation](https://github.com/pierregrothe/graphrag-api#readme)
- [API Reference](http://localhost:8001/docs)

### 📋 Compatibility
- **Python**: 3.12+
- **Platforms**: {PLATFORMS}
- **LLM Providers**: Ollama, Google Gemini
- **Authentication**: JWT, API Keys

### ⚠️ Breaking Changes
<!-- List any breaking changes -->
None in this release.

### 🚀 Migration Guide
<!-- Add migration steps if needed -->
No migration required from previous versions.

### 📝 Notes
{RELEASE_NOTES}

### 🙏 Contributors
<!-- List contributors -->
- @pierregrothe

---

**Full Changelog**: [Compare View](https://github.com/pierregrothe/graphrag-api/compare/{PREVIOUS_VERSION}...{VERSION})
