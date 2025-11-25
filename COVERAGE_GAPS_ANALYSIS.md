# Test Coverage Analysis and Gap Report

**Last Updated:** 2025-11-20 12:33:08


## 1. Overall Coverage Status

- **Current Overall Coverage:** 19.75%

- **Target Coverage:** 80.0%

- **Coverage Gap:** 60.25%

- **Total Statements:** 22,721

- **Covered Statements:** 4,760

- **Missing Statements:** 17,961


## 2. Coverage Distribution


| Coverage Range | Count | % of Total |

|---|---|---|

| 0-50% (Critical) | 198 | 80.2% |

| 50-80% (Medium) | 11 | 4.5% |

| 80-100% (Good) | 38 | 15.4% |


## 3. Critical Priority Modules (< 50% Coverage)


These modules have the lowest coverage and should be prioritized:


### explorer_backend.py

- **Coverage:** 0.00%

- **Statements:** 572 total | 0 covered | 572 missing

- **Priority:** HIGH (Core module with 572 statements)

- **Uncovered Lines (sample):** 6, 8-19, 21-24, 27, 31...



### ai\ai_assistant\personal_ai_assistant.py

- **Coverage:** 20.77%

- **Statements:** 405 total | 97 covered | 308 missing

- **Priority:** HIGH (Core module with 405 statements)

- **Uncovered Lines (sample):** 15-17, 30-31, 49-52, 55, 93...



### core\gamification.py

- **Coverage:** 46.44%

- **Statements:** 368 total | 192 covered | 176 missing

- **Priority:** HIGH (Core module with 368 statements)

- **Uncovered Lines (sample):** 27, 39-40, 42-45, 81, 117...



### core\security_middleware.py

- **Coverage:** 46.36%

- **Statements:** 347 total | 191 covered | 156 missing

- **Priority:** HIGH (Core module with 347 statements)

- **Uncovered Lines (sample):** 161, 164, 171, 173, 186-187...



### core\peer_discovery.py

- **Coverage:** 0.00%

- **Statements:** 321 total | 0 covered | 321 missing

- **Priority:** HIGH (Core module with 321 statements)

- **Uncovered Lines (sample):** 14-21, 24, 27-37



### core\xai_blockchain\ai_governance_dao.py

- **Coverage:** 24.02%

- **Statements:** 310 total | 98 covered | 212 missing

- **Priority:** HIGH (Core module with 310 statements)

- **Uncovered Lines (sample):** 90-98, 101-104, 107-110, 113-115



### core\auto_switching_ai_executor.py

- **Coverage:** 0.00%

- **Statements:** 303 total | 0 covered | 303 missing

- **Priority:** HIGH (Core module with 303 statements)

- **Uncovered Lines (sample):** 18-25, 28-29, 38-41, 44, 47-51



### generate_premine.py

- **Coverage:** 0.00%

- **Statements:** 279 total | 0 covered | 279 missing

- **Priority:** HIGH (Core module with 279 statements)

- **Uncovered Lines (sample):** 20-24, 27-31, 34-38, 41, 56...



### core\multi_ai_collaboration.py

- **Coverage:** 0.00%

- **Statements:** 272 total | 0 covered | 272 missing

- **Priority:** HIGH (Core module with 272 statements)

- **Uncovered Lines (sample):** 25-31, 34, 37-41, 44, 63...



### core\monitoring.py

- **Coverage:** 47.83%

- **Statements:** 270 total | 151 covered | 119 missing

- **Priority:** HIGH (Core module with 270 statements)

- **Uncovered Lines (sample):** 63-64, 66, 71, 82-83, 87-88...



### core\advanced_consensus.py

- **Coverage:** 43.99%

- **Statements:** 265 total | 136 covered | 129 missing

- **Priority:** HIGH (Core module with 265 statements)

- **Uncovered Lines (sample):** 76, 103, 120-121, 123, 125...



### core\blockchain_persistence.py

- **Coverage:** 0.00%

- **Statements:** 262 total | 0 covered | 262 missing

- **Priority:** HIGH (Core module with 262 statements)

- **Uncovered Lines (sample):** 12-19, 22, 26, 29-31, 34...



### core\ai_governance.py

- **Coverage:** 31.88%

- **Statements:** 262 total | 95 covered | 167 missing

- **Priority:** HIGH (Core module with 262 statements)

- **Uncovered Lines (sample):** 24, 26-29, 78-79, 81-83, 85...



### core\ai_node_operator_questioning.py

- **Coverage:** 0.00%

- **Statements:** 261 total | 0 covered | 261 missing

- **Priority:** HIGH (Core module with 261 statements)

- **Uncovered Lines (sample):** 24-28, 31, 34-37, 40, 43-47...



### core\time_capsule.py

- **Coverage:** 0.00%

- **Statements:** 253 total | 0 covered | 253 missing

- **Priority:** HIGH (Core module with 253 statements)

- **Uncovered Lines (sample):** 9-15, 17, 19, 22, 25-26...



### core\metrics.py

- **Coverage:** 0.00%

- **Statements:** 245 total | 0 covered | 245 missing

- **Priority:** HIGH (Core module with 245 statements)

- **Uncovered Lines (sample):** 16, 26-35, 40, 43, 51-52...



### integrate_ai_systems.py

- **Coverage:** 0.00%

- **Statements:** 236 total | 0 covered | 236 missing

- **Priority:** HIGH (Core module with 236 statements)

- **Uncovered Lines (sample):** 15-16, 19, 21-23, 25-28, 30-34...



### core\error_recovery_integration.py

- **Coverage:** 0.00%

- **Statements:** 234 total | 0 covered | 234 missing

- **Priority:** HIGH (Core module with 234 statements)

- **Uncovered Lines (sample):** 8, 13-15, 18, 30, 33-34...



### core\social_recovery.py

- **Coverage:** 12.50%

- **Statements:** 232 total | 39 covered | 193 missing

- **Priority:** HIGH (Core module with 232 statements)

- **Uncovered Lines (sample):** 27, 51-56, 60-65, 69-74, 78



### core\recovery_strategies.py

- **Coverage:** 0.00%

- **Statements:** 224 total | 0 covered | 224 missing

- **Priority:** HIGH (Core module with 224 statements)

- **Uncovered Lines (sample):** 12-18, 21, 29, 36-37, 39-40...



## 4. Medium Priority Modules (50-80% Coverage)


These modules need targeted testing to reach 80%:


### core\nonce_tracker.py

- **Coverage:** 56.00%

- **Gap to 80%:** 24.00%

- **Statements:** 86 total | 49 covered | 37 missing

- **Estimated Tests Needed:** 20

- **Uncovered Lines (sample):** 50-51, 55-59, 68, 81-82



### core\chain_validator.py

- **Coverage:** 58.90%

- **Gap to 80%:** 21.10%

- **Statements:** 323 total | 200 covered | 123 missing

- **Estimated Tests Needed:** 68

- **Uncovered Lines (sample):** 176-181, 193, 198, 203, 208



### core\node_api.py

- **Coverage:** 62.62%

- **Gap to 80%:** 17.38%

- **Statements:** 720 total | 479 covered | 241 missing

- **Estimated Tests Needed:** 125

- **Uncovered Lines (sample):** 229, 231, 234, 243, 246-247...



### core\wallet_trade_manager_impl.py

- **Coverage:** 67.11%

- **Gap to 80%:** 12.89%

- **Statements:** 66 total | 44 covered | 22 missing

- **Estimated Tests Needed:** 8

- **Uncovered Lines (sample):** 23, 43-44, 56, 59, 65-66...



### core\structured_logger.py

- **Coverage:** 70.55%

- **Gap to 80%:** 9.45%

- **Statements:** 141 total | 100 covered | 41 missing

- **Estimated Tests Needed:** 13

- **Uncovered Lines (sample):** 57, 64, 159-161, 170, 172...



### core\trading.py

- **Coverage:** 72.73%

- **Gap to 80%:** 7.27%

- **Statements:** 62 total | 48 covered | 14 missing

- **Estimated Tests Needed:** 4

- **Uncovered Lines (sample):** 49-50, 54, 78-79, 83, 98-99...



### core\node_consensus.py

- **Coverage:** 74.06%

- **Gap to 80%:** 5.94%

- **Statements:** 128 total | 101 covered | 27 missing

- **Estimated Tests Needed:** 7

- **Uncovered Lines (sample):** 181-183, 220, 223, 234, 283-286



### core\api_extensions.py

- **Coverage:** 74.51%

- **Gap to 80%:** 5.49%

- **Statements:** 47 total | 37 covered | 10 missing

- **Estimated Tests Needed:** 2

- **Uncovered Lines (sample):** 53, 78, 80-84, 94, 100...



### core\node.py

- **Coverage:** 77.08%

- **Gap to 80%:** 2.92%

- **Statements:** 205 total | 160 covered | 45 missing

- **Estimated Tests Needed:** 5

- **Uncovered Lines (sample):** 123-125, 127-132, 142



### core\blockchain.py

- **Coverage:** 77.54%

- **Gap to 80%:** 2.46%

- **Statements:** 395 total | 313 covered | 82 missing

- **Estimated Tests Needed:** 9

- **Uncovered Lines (sample):** 309, 312, 346-347, 349-350, 364...



### core\blockchain_storage.py

- **Coverage:** 78.70%

- **Gap to 80%:** 1.30%

- **Statements:** 92 total | 73 covered | 19 missing

- **Estimated Tests Needed:** 2

- **Uncovered Lines (sample):** 57, 91-93, 107-109, 117, 128-129



## 5. High-Impact Modules from Task


These are critical modules mentioned in the task:


### core\node_api.py

- **Coverage:** 62.62% (HIGH Priority)

- **Gap to 80%:** 17.38%

- **Statements:** 720 | Covered: 479 | Missing: 241

- **Estimated Tests to Reach 80%:** 125

- **Uncovered Lines (sample):** 229, 231, 234, 243, 246-247...



### core\node.py

- **Coverage:** 77.08% (MEDIUM Priority)

- **Gap to 80%:** 2.92%

- **Statements:** 205 | Covered: 160 | Missing: 45

- **Estimated Tests to Reach 80%:** 5

- **Uncovered Lines (sample):** 123-125, 127-132, 142-143, 149, 156-157...



### core\blockchain_security.py

- **Coverage:** 94.15% (MEDIUM Priority)

- **Gap to 80%:** -14.15%

- **Statements:** 299 | Covered: 287 | Missing: 12



### core\hardware_wallet.py

- **Coverage:** 0.00% (CRITICAL Priority)

- **Gap to 80%:** 80.00%

- **Statements:** 15 | Covered: 0 | Missing: 15

- **Estimated Tests to Reach 80%:** 12

- **Uncovered Lines (sample):** 7, 10-11, 14, 17, 20...



## 6. Prioritized Action Plan to Reach 80%


### Phase 1: High-Impact Modules (Greatest Coverage Gain)


1. **explorer_backend.py** - Impact: +457.6 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 457

2. **core\peer_discovery.py** - Impact: +256.8 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 256

3. **core\auto_switching_ai_executor.py** - Impact: +242.4 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 242

4. **ai\ai_assistant\personal_ai_assistant.py** - Impact: +239.9 statements

   - Current: 20.8% | Gap: 59.2% | Est. Tests: 239

5. **generate_premine.py** - Impact: +223.2 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 223

6. **core\multi_ai_collaboration.py** - Impact: +217.6 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 217

7. **core\blockchain_persistence.py** - Impact: +209.6 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 209

8. **core\ai_node_operator_questioning.py** - Impact: +208.8 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 208

9. **core\time_capsule.py** - Impact: +202.4 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 202

10. **core\metrics.py** - Impact: +196.0 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 196


### Phase 2: Medium-Impact Modules


11. **integrate_ai_systems.py** - Impact: +188.8 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 188

12. **core\error_recovery_integration.py** - Impact: +187.2 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 187

13. **core\recovery_strategies.py** - Impact: +179.2 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 179

14. **core\aml_compliance.py** - Impact: +173.6 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 173

15. **core\xai_blockchain\ai_governance_dao.py** - Impact: +173.5 statements

   - Current: 24.0% | Gap: 56.0% | Est. Tests: 173

16. **core\governance_transactions.py** - Impact: +172.8 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 172

17. **core\jwt_auth_manager.py** - Impact: +172.8 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 172

18. **core\input_validation_schemas.py** - Impact: +171.2 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 171

19. **core\secure_api_key_manager.py** - Impact: +171.2 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 171

20. **core\ai_trading_bot.py** - Impact: +169.6 statements

   - Current: 0.0% | Gap: 80.0% | Est. Tests: 169


## 7. Summary Statistics


- **Total modules below 80%:** 209

- **Estimated statements to cover:** 13,941

- **Estimated new tests needed:** 697

- **Potential coverage improvement:** From 19.7% to 80%+


## 8. Testing Recommendations


1. **Focus on Critical Modules First**: Start with modules at 0-50% coverage

2. **Target High-Impact Modules**: Prioritize modules with many statements

3. **Use Coverage-Driven Development**: Write tests that explicitly target missing lines

4. **Leverage pytest-cov**: Use `--cov-report=html` for visual coverage inspection

5. **Implement Incrementally**: Add tests in phases to track progress

6. **Focus on Module Categories**: Group related modules and test together

