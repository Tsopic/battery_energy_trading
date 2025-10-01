# Battery Energy Trading - TODO

## Current Sprint: Multi-Peak Discharge Testing & Refinement

### Testing Phase (RED-GREEN-REFACTOR)
- [x] Run existing test suite to verify battery state projection tests pass (18/18 passing)
- [ ] Add integration test for multi-peak discharge with real price data
- [ ] Test solar recharge calculation with various datetime formats
- [ ] Verify backward compatibility (without solar forecast)
- [ ] Test dashboard battery state visibility

### Code Quality & Refactoring
- [ ] Review and optimize battery state projection performance
- [ ] Add comprehensive docstrings to new methods
- [ ] Ensure proper error handling in solar forecast parsing
- [ ] Code review: check for potential edge cases

### Documentation
- [ ] Update README with multi-peak discharge feature
- [ ] Create user guide for multi-peak configuration
- [ ] Document battery state projection algorithm
- [ ] Add troubleshooting section for solar forecast issues

### Future Enhancements
- [ ] Runtime feasibility validation
- [ ] Adaptive slot re-evaluation
- [ ] Multi-day battery state projection enhancement
- [ ] Battery SoC safety margins

## Completed
- [x] Multi-day optimization default changed to OFF
- [x] Battery state projection method implemented
- [x] Solar recharge calculation between slots
- [x] Feasibility-based discharge slot selection
- [x] Dashboard visibility enhancements
- [x] Comprehensive test coverage added
