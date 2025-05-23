# 선박 중앙 냉각 시스템 최적화 프로그램

이 프로그램은 선박의 중앙 냉각 시스템에서 Fresh Water Pump (F.W. Pump) 및 Sea Water Pump (S.W. Pump)의 주파수를 최적 조절하여 에너지 절감 및 냉각 성능을 극대화하는 시스템입니다.

## 주요 기능

1. **열교환기 온도 제어 및 T5 자동 계산**
   - T5(F.W. Outlet Temperature)는 F.W. 및 S.W.의 유량, 온도에 따라 동적으로 계산
   - 계산 공식: T5 = T4 - (mSW/mFW) × (T2-T1)

2. **F.W. Pump 주파수 조절 로직**
   - ΔT = (T4 - 36)을 기준으로 주파수 조절
   - PID 제어 적용 (P = 1.5, I = 0.05, D = 0.02)
   - 주파수 범위: 40Hz ~ 60Hz

3. **S.W. Pump 주파수 조절 로직**
   - T5가 36°C 초과 시 → 주파수 증가
   - T5가 34°C 미만 시 → 주파수 감소
   - 주파수 범위: 35Hz ~ 60Hz

4. **비상 보호 로직**
   - 센서 오류 시 기본 주파수 유지 (45Hz)
   - 급격한 온도 변화 발생 시 알람 발생 및 속도 변화 제한
   - 주파수 조절 속도 제한 (초당 0.5Hz ~ 1Hz)

5. **데이터 로깅 및 시각화**
   - 실시간 온도, 주파수, 유량 데이터 시각화
   - CSV 파일로 데이터 저장

## 설치 방법

1. 필요한 패키지 설치:
```
pip install -r requirements.txt
```

2. 프로그램 실행:
```
python NEW_AI.py
```

## 시스템 요구사항

- Python 3.7 이상
- numpy
- matplotlib

## 사용 방법

1. 프로그램을 실행하면 실시간 모니터링 UI가 표시됩니다.
2. 상단 그래프는 온도 데이터(T1, T2, T4, T5)를 보여줍니다.
3. 중간 그래프는 펌프 주파수(F.W. Pump, S.W. Pump)를 보여줍니다.
4. 하단 그래프는 유량 데이터와 시스템 상태를 보여줍니다.
5. 프로그램 종료 시 자동으로 데이터가 CSV 파일로 저장됩니다.

## 주의사항

- 현재 버전은 시뮬레이션 모드로 동작합니다.
- 실제 시스템 연동을 위해서는 PLC, MODBUS, Ethernet 등의 통신 모듈 추가 구현이 필요합니다.

## 향후 개선 사항

- AI 기반 머신러닝 최적화 적용
- 실제 데이터 기반 튜닝 인터페이스 제공
- 다양한 통신 프로토콜 지원 (MODBUS, CAN, Ethernet) #   �\�ȸ�  tǄ� 
 # ���  �|�  ��\�ܴ 
 