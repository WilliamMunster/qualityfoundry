"""QualityFoundry - Policy Routes (L1)

当前策略只读 API，解决前端策略选择空库问题。
"""
from fastapi import APIRouter

from qualityfoundry.governance.policy_loader import get_policy
from qualityfoundry.governance.repro import get_git_sha, get_deps_fingerprint

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/current")
def get_current_policy():
    """获取当前策略配置（只读）。
    
    返回当前生效的策略元信息，前端可直接展示，
    无需进行策略版本管理。
    
    Returns:
        包含策略版本、哈希、Git SHA 和依赖指纹的字典
    """
    policy = get_policy()
    
    # 计算策略哈希
    import hashlib
    import json
    policy_json = json.dumps(policy.model_dump(), sort_keys=True, ensure_ascii=False)
    policy_hash = hashlib.sha256(policy_json.encode()).hexdigest()[:16]
    
    return {
        "version": policy.version,
        "policy_hash": policy_hash,
        "git_sha": get_git_sha(),
        "deps_fingerprint": get_deps_fingerprint()[:16] if get_deps_fingerprint() else None,
        "source": "governance/policy_config.yaml",
        # 只返回安全的元信息，不暴露敏感策略细节
        "summary": {
            "high_risk_keywords_count": len(policy.high_risk_keywords),
            "high_risk_patterns_count": len(policy.high_risk_patterns),
            "tools_allowlist_count": len(policy.tools.allowlist),
            "cost_governance": {
                "timeout_s": policy.cost_governance.timeout_s,
                "max_retries": policy.cost_governance.max_retries,
            },
        },
    }
