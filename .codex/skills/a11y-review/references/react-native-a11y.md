# React Native Accessibility Checklist

Mark items PASS/FAIL/UNKNOWN and cite evidence (component/file).

## Labels & Roles

- All actionable elements have `accessibilityRole` where relevant (PASS/FAIL/UNKNOWN):
- All actionable elements have a useful `accessibilityLabel` (PASS/FAIL/UNKNOWN):
- State is conveyed with `accessibilityState` where relevant (PASS/FAIL/UNKNOWN):

## Focus & Navigation

- Focus order is logical (PASS/FAIL/UNKNOWN):
- Important containers are grouped appropriately (`accessible`, `importantForAccessibility`) (PASS/FAIL/UNKNOWN):

## Dynamic Type

- Text supports font scaling without clipping/truncation (PASS/FAIL/UNKNOWN):

## Touch Targets

- Tap targets meet minimum sizes for comfortable use (PASS/FAIL/UNKNOWN):

## Motion

- Reduced motion respected where animations exist (PASS/FAIL/UNKNOWN):

