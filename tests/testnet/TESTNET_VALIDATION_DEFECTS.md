# XAI Testnet Validation - Defect Tracking

**Version:** 1.0
**Date:** November 21, 2025
**Test Phase:** Initial Validation
**Testnet Version:** 1.0.0

---

## Active Defects


**Severity:** P0 - Critical
**Status:** Identified
**Reported:** 2025-11-21
**Component:** Infrastructure - EC2 Bootstrap Script
**Environment:** AWS us-east-1

**Description:**

**Root Cause:**
```bash
# Line 52 in user_data.sh
```

The placeholder URL fails with "repository not found". Without the code, the systemd service `xai-node` cannot start, leaving no process listening on port 5000.

**Impact:**
- Blockchain application never gets installed on EC2 instances
- No process listening on port 5000 (API port)
- All load balancer health checks fail (Target.FailedHealthChecks)
- Instances remain in "unhealthy" state indefinitely
- API endpoints continue returning 503 errors despite DEFECT-001 fix
- Testnet is completely non-functional

**Solution Options:**
1. **S3 Deployment**: Package code, upload to S3, download in user_data (fastest)
2. **Docker/ECR**: Create Docker image, push to ECR, pull in user_data
3. **Custom AMI**: Bake AMI with code pre-installed

**Recommended Solution:** S3 deployment - fastest to implement for immediate testing

**Priority:** P0 - Blocking all testnet functionality

---

### DEFECT-001: ASG Not Registered with Load Balancer Target Group

**Severity:** P0 - Critical
**Status:** RESOLVED
**Reported:** 2025-11-21
**Component:** Infrastructure - Auto Scaling Group
**Environment:** AWS us-east-1

**Description:**
The Auto Scaling Group `xai-nodes-primary-asg` is not configured to register instances with the Application Load Balancer target group `xai-api-tg`. This causes all API requests to return HTTP 503 errors because there are no healthy targets behind the load balancer.

**Root Cause:**
Terraform configuration in `deploy/aws/terraform/main.tf` (lines 241-267) is missing the `target_group_arns` parameter in the `aws_autoscaling_group.blockchain_nodes_primary` resource.

**Current Code (Defective):**
```terraform
resource "aws_autoscaling_group" "blockchain_nodes_primary" {
  name                = "xai-nodes-primary-asg"
  vpc_zone_identifier = module.vpc_primary.public_subnets
  desired_capacity    = 2
  min_size            = 2
  max_size            = 4

  launch_template {
    id      = aws_launch_template.blockchain_node.id
    version = "$Latest"
  }

  health_check_type         = "EC2"
  health_check_grace_period = 300

  # MISSING: target_group_arns parameter
}
```

**Expected Code (Fixed):**
```terraform
resource "aws_autoscaling_group" "blockchain_nodes_primary" {
  name                = "xai-nodes-primary-asg"
  vpc_zone_identifier = module.vpc_primary.public_subnets
  desired_capacity    = 2
  min_size            = 2
  max_size            = 4

  launch_template {
    id      = aws_launch_template.blockchain_node.id
    version = "$Latest"
  }

  # FIX: Add target group registration
  target_group_arns = [aws_lb_target_group.api.arn]

  # FIX: Change health check type to ELB
  health_check_type         = "ELB"
  health_check_grace_period = 300
}
```

**Impact:**
- All API endpoints return HTTP 503 Service Temporarily Unavailable
- Block Explorer is inaccessible
- Faucet is inaccessible
- Testnet cannot be used by external users
- All API endpoint tests fail (P0 tests)

**Test Results Affected:**
- API-001: Health Endpoint - FAILED (503 error)
- API-002: Blockchain Status - FAILED (503 error)
- API-003: Latest Block - FAILED (503 error)
- All other API endpoints - FAILED

**Infrastructure Status:**
✅ Load Balancer: Active and healthy
✅ Target Group: Created successfully (port 5000)
✅ Auto Scaling Group: Created successfully
✅ EC2 Instances: 2 instances running and healthy
❌ Target Registration: NO instances registered in target group
❌ API Endpoints: All returning 503 errors

**EC2 Instance Details:**
- Instance 1: i-088710540a2683da9 (running, healthy, InService)
  - Private IP: 10.0.102.180
  - Subnet: subnet-0304e235f3188f41c (us-east-1b)
- Instance 2: i-0e4e635c3af0c3837 (running, healthy, InService)
  - Private IP: 10.0.101.112
  - Subnet: subnet-05ebe242be426a4d8 (us-east-1a)

**Remediation Plan:**
1. Update Terraform configuration to add `target_group_arns`
2. Change `health_check_type` from "EC2" to "ELB"
3. Run `terraform apply` to update ASG configuration
4. Wait for instances to register with target group
5. Verify health checks pass
6. Retest all API endpoints

**Priority:** P0 - Must fix before testnet can be used

---

## Resolved Defects

### DEFECT-001: ASG Not Registered with Load Balancer Target Group [RESOLVED]

**Resolution Date:** 2025-11-21
**Resolution:** Updated Terraform configuration in `main.tf` lines 254, 257-258:
- Added `target_group_arns = [aws_lb_target_group.api.arn]`
- Changed `health_check_type` from "EC2" to "ELB"
**Applied:** `terraform apply` completed successfully
**Verified:** Both instances now registered with target group (though unhealthy due to DEFECT-002)

---

## Defect Summary

| Severity | Count | Open | Resolved |
|----------|-------|------|----------|
| P0 (Critical) | 2 | 1 | 1 |
| P1 (Major) | 0 | 0 | 0 |
| P2 (Minor) | 0 | 0 | 0 |
| **Total** | **2** | **1** | **1** |

---

## Next Actions

1. ✅ DEFECT-001: Fixed - ASG now registers with target group
2. 🔄 DEFECT-002: In Progress - Need to deploy code to instances
   - Package codebase into tarball
   - Create S3 bucket for deployment artifacts
   - Upload tarball to S3
   - Trigger instance replacement to apply new user_data
3. Verify instances become healthy after code deployment
4. Re-run all failed API endpoint tests
5. Continue with remaining validation test suite
