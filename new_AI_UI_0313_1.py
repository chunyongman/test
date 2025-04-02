import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import logging
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
import random

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cooling_system.log"),
        logging.StreamHandler()
    ]
)

# 랜덤 데이터 생성 모듈 추가
class RandomDataGenerator:
    """실제 조건에 맞는 랜덤 데이터 생성 모듈"""
    
    # 점진적 변화를 위한 클래스 변수 추가
    current_t1 = 25.0  # S.W. 입구 온도 초기값
    current_t4 = 40.0  # F.W. 입구 온도 초기값
    t1_direction = 1   # 1: 증가, -1: 감소
    t4_direction = 1   # 1: 증가, -1: 감소
    t1_change_rate = 0.2  # 한 번에 변화하는 최대 온도 (°C)
    t4_change_rate = 0.3  # 한 번에 변화하는 최대 온도 (°C)
    
    @staticmethod
    def generate_t1_temperature():
        """
        실제 바닷물 온도 변화를 반영한 T1 값 생성 (0~36°C)
        점진적으로 증가하다가 감소하는 패턴 구현
        """
        # 현재 방향에 따라 온도 변화
        change = RandomDataGenerator.t1_change_rate * RandomDataGenerator.t1_direction
        
        # 약간의 랜덤성 추가 (변화율의 50~100% 사이)
        change *= random.uniform(0.5, 1.0)
        
        # 현재 온도 업데이트
        RandomDataGenerator.current_t1 += change
        
        # 온도 범위 제한 및 방향 전환
        if RandomDataGenerator.current_t1 >= 36.0:
            RandomDataGenerator.current_t1 = 36.0
            RandomDataGenerator.t1_direction = -1  # 감소 방향으로 전환
        elif RandomDataGenerator.current_t1 <= 0.0:
            RandomDataGenerator.current_t1 = 0.0
            RandomDataGenerator.t1_direction = 1   # 증가 방향으로 전환
        
        # 일정 확률(5%)로 방향 전환 (자연스러운 변화를 위해)
        if random.random() < 0.05:
            RandomDataGenerator.t1_direction *= -1
        
        return RandomDataGenerator.current_t1
    
    @staticmethod
    def generate_t4_temperature():
        """
        Central Cooling System에서 발생할 수 있는 T4 값 생성 (36~53°C)
        점진적으로 증가하다가 감소하는 패턴 구현
        """
        # 현재 방향에 따라 온도 변화
        change = RandomDataGenerator.t4_change_rate * RandomDataGenerator.t4_direction
        
        # 약간의 랜덤성 추가 (변화율의 50~100% 사이)
        change *= random.uniform(0.5, 1.0)
        
        # 현재 온도 업데이트
        RandomDataGenerator.current_t4 += change
        
        # 온도 범위 제한 및 방향 전환
        if RandomDataGenerator.current_t4 >= 53.0:
            RandomDataGenerator.current_t4 = 53.0
            RandomDataGenerator.t4_direction = -1  # 감소 방향으로 전환
        elif RandomDataGenerator.current_t4 <= 36.0:
            RandomDataGenerator.current_t4 = 36.0
            RandomDataGenerator.t4_direction = 1   # 증가 방향으로 전환
        
        # 일정 확률(5%)로 방향 전환 (자연스러운 변화를 위해)
        if random.random() < 0.05:
            RandomDataGenerator.t4_direction *= -1
        
        return RandomDataGenerator.current_t4
    
    @staticmethod
    def generate_dp1_pressure():
        """실제 조건에 맞는 DP1 값 생성 (0.5~2.5 bar)"""
        # 정상 운전 범위 내에서 랜덤 값 생성
        return random.uniform(0.5, 2.5)
    
    @staticmethod
    def generate_engine_load():
        """실제 엔진 부하 조건 생성 (10~100%)"""
        # 엔진 부하 분포
        # 10~30%: 저부하 (20% 확률)
        # 30~70%: 중부하 (50% 확률)
        # 70~100%: 고부하 (30% 확률)
        
        distribution = random.random()  # 0~1 사이 랜덤 값
        
        if distribution < 0.2:  # 20% 확률
            # 저부하 (10~30%)
            return random.uniform(10, 30)
        elif distribution < 0.7:  # 50% 확률
            # 중부하 (30~70%)
            return random.uniform(30, 70)
        else:  # 30% 확률
            # 고부하 (70~100%)
            return random.uniform(70, 100)

class CoolingSystemController:
    """냉각 시스템 컨트롤러 클래스"""
    
    def __init__(self):
        """초기화"""
        # 온도 변수 (°C)
        self.T1 = 25.0  # S.W. 입구 온도
        self.T2 = 30.0  # S.W. 출구 온도
        self.T4 = 36.0  # F.W. 입구 온도
        self.T5 = 32.0  # F.W. 출구 온도
        
        # 차압 변수 (bar)
        self.DP1 = 1.5  # S.W. 입구 차압
        
        # 펌프 변수
        self.fw_pump_freq = 45.0  # F.W. 펌프 주파수 (Hz)
        self.fw_pump_count = 2    # F.W. 펌프 동작 개수
        self.sw_pump_freq = 45.0  # S.W. 펌프 주파수 (Hz)
        self.sw_pump_count = 2    # S.W. 펌프 동작 개수
        
        # 유량 변수 (m³/h)
        self.m_FW = 250.0  # F.W. 유량
        self.m_SW = 300.0  # S.W. 유량
        
        # 열교환기 효율 (%)
        self.heat_exchanger_efficiency = 0.85
        self.heat_exchanger_age = 0  # 열교환기 사용 시간 (시뮬레이션용)
        
        # 엔진 부하 (%)
        self.engine_load = 75.0
        
        # 시스템 상태
        self.simulation_mode = True  # 시뮬레이션 모드 여부
        self.user_input_mode = False  # 사용자 입력 모드 여부
        self.alarm_active = False  # 알람 상태
        self.alarm_message = ""  # 알람 메시지
        
        # 시간 관련 변수
        self.last_update_time = time.time()
        self.operating_hours = 0.0  # 운전 시간 (시간)
        self.time_data = []  # 시간 데이터 저장용
        
        # 데이터 로깅을 위한 리스트
        self.t1_data = []
        self.t2_data = []
        self.t4_data = []
        self.t5_data = []
        self.dp1_data = []
        self.fw_freq_data = []
        self.sw_freq_data = []
        self.fw_count_data = []
        self.sw_count_data = []
        self.efficiency_data = []
        self.engine_load_data = []
        
        # 초기화 로그
        logging.info("냉각 시스템 컨트롤러 초기화 완료")
        logging.info(f"초기 상태: T1={self.T1:.1f}°C, T2={self.T2:.1f}°C, T4={self.T4:.1f}°C, T5={self.T5:.1f}°C, DP1={self.DP1:.2f}bar")
        
        # 초기 계산
        self.update_system()
    
    def calculate_t2(self):
        """S.W. 출구 온도(T2) 계산"""
        # T2는 calculate_t5() 메서드에서 계산되므로 해당 메서드 호출
        self.calculate_t5()
        return self.T2
        
    def calculate_t5(self):
        """F.W. 출구 온도(T5) 계산"""
        # 열교환기에서의 열전달 원리: 담수가 잃는 열 = 해수가 얻는 열
        # 열교환기 효율(ε)은 0.75로 설정
        
        # 열용량 (J/kg·K)
        cp_fw = 4200  # 담수 비열
        cp_sw = 4000  # 해수 비열
        
        # 밀도 (kg/m³)
        rho_fw = 1000  # 담수 밀도
        rho_sw = 1025  # 해수 밀도
        
        # 열용량률 계산 (W/K)
        C_fw = self.m_FW * rho_fw * cp_fw / 3600  # m³/h를 kg/s로 변환 (÷3600)
        C_sw = self.m_SW * rho_sw * cp_sw / 3600  # m³/h를 kg/s로 변환 (÷3600)
        
        # 열교환기 효율
        epsilon = 0.75  # 열교환기 효율 (고정값)
        
        # 열교환 방정식 적용
        if C_fw <= 0 or C_sw <= 0:
            # 유량이 0이면 T4와 동일하게 설정
            self.T5 = self.T4
        else:
            # 최소 열용량률 결정 (열전달 제한 요소)
            C_min = min(C_fw, C_sw)
            
            if C_min == C_fw:
                # 담수 측 열용량률이 더 작은 경우
                self.T5 = self.T4 - epsilon * (self.T4 - self.T1)
            else:
                # 해수 측 열용량률이 더 작은 경우
                self.T5 = self.T4 - (epsilon * C_sw * (self.T4 - self.T1)) / C_fw
        
        # 물리적 제약 적용
        # T5는 T4보다 높을 수 없음 (담수는 열을 잃음)
        self.T5 = min(self.T4, self.T5)
        # T5는 T1보다 낮을 수 없음 (열역학 제2법칙)
        self.T5 = max(self.T1, self.T5)
        
        # T2 계산 (에너지 보존 법칙)
        if C_sw > 0:
            # 담수가 잃는 열 = 해수가 얻는 열
            # C_fw * (T4 - T5) = C_sw * (T2 - T1)
            self.T2 = self.T1 + (C_fw * (self.T4 - self.T5)) / C_sw
            # T2는 T4보다 높을 수 없음 (열역학 제2법칙)
            self.T2 = min(self.T4, self.T2)
        else:
            # 해수 유량이 0이면 T1과 동일하게 설정
            self.T2 = self.T1
        
        return self.T5
    
    def update_heat_exchanger_efficiency(self):
        """열교환기 효율 동적 업데이트"""
        # 열교환기 효율은 0.75로 고정
        self.heat_exchanger_efficiency = 0.75
    
    def update_flow_rates(self):
        """펌프 주파수와 대수에 따른 유량 계산"""
        # F.W. 유량 계산 (주파수와 펌프 대수에 비례)
        # 기준: 1290 m³/h (60Hz, 1대 기준)
        base_fw_flow = 1290.0  # 기본 유량 (m³/h) - 60Hz, 1대 기준
        self.m_FW = base_fw_flow * (self.fw_pump_freq / 60.0) * self.fw_pump_count
        
        # S.W. 유량 계산 (주파수와 펌프 대수에 비례)
        # 기준: 1500 m³/h (60Hz, 1대 기준)
        base_sw_flow = 1500.0  # 기본 유량 (m³/h) - 60Hz, 1대 기준
        self.m_SW = base_sw_flow * (self.sw_pump_freq / 60.0) * self.sw_pump_count
        
        # 유량 로깅
        logging.debug(f"유량 계산: F.W.={self.m_FW:.1f}m³/h, S.W.={self.m_SW:.1f}m³/h")
        logging.debug(f"펌프 상태: F.W.={self.fw_pump_count}대/{self.fw_pump_freq:.1f}Hz, S.W.={self.sw_pump_count}대/{self.sw_pump_freq:.1f}Hz")
    
    def adjust_fw_pump_frequency(self):
        """F.W. 펌프 주파수 조절"""
        # 현재 시간 기록
        current_time = time.time()
        elapsed_time = current_time - self.last_update_time
        
        # 델타T 계산 (T4-36)
        delta_t = self.T4 - 36.0
        
        # 델타T에 따른 목표 주파수 계산
        desired_freq = 0.0
        
        if delta_t >= 17.0:  # 임계값 복원 (14.0 -> 17.0)
            # 델타T가 17 이상이면 최대 주파수 (60Hz)
            desired_freq = 60.0
            logging.info(f"델타T 높음({delta_t:.1f}°C): F.W. 펌프 주파수 최대 -> 60.0Hz")
        elif delta_t <= 0:
            # 델타T가 0 이하면 최소 주파수 (40Hz)
            desired_freq = 40.0
            logging.info(f"델타T 낮음({delta_t:.1f}°C): F.W. 펌프 주파수 최소 -> 40.0Hz")
        else:
            # 델타T가 0~17 사이면 비례하여 주파수 계산 (40Hz~60Hz)
            # 선형 비례: 40 + (delta_t / 17) * (60 - 40)
            desired_freq = 40.0 + (delta_t / 17.0) * 20.0
            logging.info(f"델타T 중간({delta_t:.1f}°C): F.W. 펌프 주파수 -> {desired_freq:.1f}Hz")
        
        # 주파수 범위 제한 (40Hz~60Hz)
        desired_freq = max(40.0, min(60.0, desired_freq))
        
        # 목표 주파수로 즉시 설정 (점진적 변화 제거)
        if self.fw_pump_freq != desired_freq:
            logging.info(f"F.W. 펌프 주파수 변경: {self.fw_pump_freq:.1f}Hz -> {desired_freq:.1f}Hz")
            self.fw_pump_freq = desired_freq
        else:
            logging.info(f"F.W. 펌프 주파수 유지: {desired_freq:.1f}Hz")
        
        # 주파수 변경 로깅
        logging.debug(f"F.W. 펌프 주파수 조절: {self.fw_pump_freq:.1f}Hz")
        
        return self.fw_pump_freq
    
    def adjust_sw_pump_frequency(self):
        """S.W. 펌프 주파수 조절"""
        # 현재 시간 기록
        current_time = time.time()
        
        # 기준 주파수는 60Hz에서 시작
        if not hasattr(self, 'sw_base_freq'):
            self.sw_base_freq = 60.0
            self.sw_pump_freq = 60.0
            self.prev_t5 = self.T5
            self.t5_direction = None  # 온도 변화 방향 (None, 'up', 'down')
            self.last_adjustment = None  # 마지막 조절 방향 (None, 'up', 'down')
            logging.info(f"S.W. 펌프 기준 주파수 초기화: {self.sw_base_freq:.1f}Hz")
        
        # 이전 T5 값과 비교하여 온도 변화 방향 결정
        if self.T5 > self.prev_t5 + 0.05:  # 0.05도 이상 상승
            current_direction = 'up'
        elif self.T5 < self.prev_t5 - 0.05:  # 0.05도 이상 하강
            current_direction = 'down'
        else:
            current_direction = self.t5_direction  # 변화가 미미하면 이전 방향 유지
        
        # 온도 변화 방향이 바뀌었는지 확인
        direction_changed = (self.t5_direction is not None and 
                            current_direction is not None and 
                            self.t5_direction != current_direction)
        
        # T5 온도에 따른 주파수 조절 결정
        if self.T5 > 36.0:
            # T5가 너무 높으면 주파수 증가 필요
            if self.last_adjustment != 'up' or not direction_changed:
                # 주파수 2Hz 증가
                desired_freq = self.sw_pump_freq + 2.0
                self.last_adjustment = 'up'
                logging.info(f"T5 온도 높음({self.T5:.1f}°C): S.W. 펌프 주파수 증가 -> {desired_freq:.1f}Hz")
            else:
                # 온도 변화 방향이 바뀌었으면 조절 중지
                desired_freq = self.sw_pump_freq
                logging.info(f"T5 온도 방향 변경(상승→하강): S.W. 펌프 주파수 유지 -> {desired_freq:.1f}Hz")
                
        elif self.T5 < 34.0:
            # T5가 너무 낮으면 주파수 감소 필요
            if self.last_adjustment != 'down' or not direction_changed:
                # 주파수 2Hz 감소
                desired_freq = self.sw_pump_freq - 2.0
                self.last_adjustment = 'down'
                logging.info(f"T5 온도 낮음({self.T5:.1f}°C): S.W. 펌프 주파수 감소 -> {desired_freq:.1f}Hz")
            else:
                # 온도 변화 방향이 바뀌었으면 조절 중지
                desired_freq = self.sw_pump_freq
                logging.info(f"T5 온도 방향 변경(하강→상승): S.W. 펌프 주파수 유지 -> {desired_freq:.1f}Hz")
        else:
            # 34~36도 사이는 적정 온도 범위로 간주하고 현재 주파수 유지
            desired_freq = self.sw_pump_freq
            logging.info(f"T5 온도 적정({self.T5:.1f}°C): S.W. 펌프 주파수 유지 -> {desired_freq:.1f}Hz")
        
        # 주파수 범위 제한 (35Hz~60Hz)
        desired_freq = max(35.0, min(60.0, desired_freq))
        
        # 목표 주파수로 즉시 설정
        if self.sw_pump_freq != desired_freq:
            logging.info(f"S.W. 펌프 주파수 변경: {self.sw_pump_freq:.1f}Hz -> {desired_freq:.1f}Hz")
            self.sw_pump_freq = desired_freq
        
        # 현재 T5와 방향 저장
        self.prev_t5 = self.T5
        self.t5_direction = current_direction
        
        return self.sw_pump_freq
    
    def check_alarm_conditions(self):
        """알람 조건 확인"""
        # 이전 알람 상태 저장
        previous_alarm = self.alarm_active
        previous_message = self.alarm_message
        
        # 알람 상태 초기화
        self.alarm_active = False
        self.alarm_message = ""
        
        # T5 온도 알람 (F.W. 출구 온도)
        if self.T5 > 40.0:
            self.alarm_active = True
            self.alarm_message = f"F.W. 출구 온도(T5) 높음: {self.T5:.1f}°C"
            logging.warning(self.alarm_message)
        # F.W. 출구 온도(T5)가 낮을 때는 경고 메시지 표시하지 않음
        # elif self.T5 < 30.0:
        #     self.alarm_active = True
        #     self.alarm_message = f"F.W. 출구 온도(T5) 낮음: {self.T5:.1f}°C"
        #     logging.warning(self.alarm_message)
            
        # T2 온도 알람 (S.W. 출구 온도)
        if self.T2 > 49.0:
            self.alarm_active = True
            self.alarm_message = f"S.W. 출구 온도(T2) 높음: {self.T2:.1f}°C"
            logging.warning(self.alarm_message)
            
        # DP1 알람 (S.W. 입구 차압)
        if self.DP1 < 0.5:
            self.alarm_active = True
            self.alarm_message = f"S.W. 입구 차압(DP1) 낮음: {self.DP1:.2f}bar"
            logging.warning(self.alarm_message)
        elif self.DP1 > 2.5:
            self.alarm_active = True
            self.alarm_message = f"S.W. 입구 차압(DP1) 높음: {self.DP1:.2f}bar"
            logging.warning(self.alarm_message)
            
        # 알람 상태 변경 시 로그 출력
        if self.alarm_active != previous_alarm or (self.alarm_active and self.alarm_message != previous_message):
            if self.alarm_active:
                logging.warning(f"알람 발생: {self.alarm_message}")
            else:
                logging.info("알람 해제")
                
        return self.alarm_active
    
    def simulate_temperature_changes(self):
        """온도 변화 시뮬레이션"""
        # 현재 시간 기록
        current_time = time.time()
        
        # 랜덤 변화 (작은 변동)
        t1_change = 0.05 * np.random.randn()  # S.W. 입구 온도 변화
        t4_change = 0.05 * np.random.randn()  # F.W. 입구 온도 변화
        
        # 엔진 부하 변화 로직 제거 - 입력창에서 주어진 값만 사용
        # 엔진 부하는 manual_update 메서드를 통해서만 변경됨
        
        # 온도 업데이트
        self.T1 += t1_change
        self.T4 += t4_change
        
        # 온도 범위 제한
        self.T1 = max(0, min(36, self.T1))  # S.W. 입구 온도 범위 제한 (0~36°C)
        self.T4 = max(36, min(53, self.T4))  # F.W. 입구 온도 범위 제한 (36~53°C)
        
        # DP1은 사용자 입력으로만 설정되므로 자동 계산하지 않음
        
        # 열교환기 효율 업데이트 (운전 시간에 따라 감소)
        age_factor = max(0.6, 1.0 - (self.operating_hours / 10000.0))  # 10,000시간 후 60%로 감소
        self.heat_exchanger_efficiency = 0.85 * age_factor
    
    def update_system(self):
        """시스템 상태 업데이트"""
        # 현재 시간 기록
        current_time = time.time()
        elapsed_time = current_time - self.last_update_time
        self.last_update_time = current_time
        
        # 운전 시간 업데이트 (시간 단위)
        self.operating_hours += elapsed_time / 3600.0
        
        # 시뮬레이션 모드에서만 자동 업데이트
        if self.simulation_mode and not self.user_input_mode:
            # 온도 변화 시뮬레이션
            self.simulate_temperature_changes()
        
        # 초기 상태 확인 (T5가 T4와 거의 같으면 초기 상태로 간주)
        if abs(self.T5 - self.T4) < 0.1:
            # 초기 상태에서는 T5를 T4보다 2도 낮게 설정
            self.T5 = self.T4 - 2.0
            logging.info(f"초기 상태 감지: T5를 {self.T5:.1f}°C로 설정")
        
        # T2와 T5 계산을 번갈아가며 수행하여 수렴 촉진
        for i in range(3):  # 3회 반복하여 수렴 촉진
            # T2 계산 (S.W. 출구 온도)
            old_t2 = self.T2
            self.calculate_t2()
            
            # T5 계산 (F.W. 출구 온도)
            old_t5 = self.T5
            self.calculate_t5()
            
            # 변화량 로깅
            logging.debug(f"반복 {i+1}: T2 변화={self.T2-old_t2:.2f}°C, T5 변화={self.T5-old_t5:.2f}°C")
            
            # 변화가 미미하면 조기 종료
            if abs(self.T2-old_t2) < 0.01 and abs(self.T5-old_t5) < 0.01:
                break
                
        # 유량 계산 업데이트
        self.update_flow_rates()
        
        # 열교환기 효율 업데이트
        self.update_heat_exchanger_efficiency()
        
        # 펌프 주파수 조절 - 먼저 수행하여 주파수 계산 우선
        self.adjust_fw_pump_frequency()
        self.adjust_sw_pump_frequency()
        
        # 펌프 대수 조정 (엔진 부하 기반)
        self.adjust_pump_count_by_load()
        
        # 주파수 변경 로깅 (최종 결정된 주파수)
        logging.info(f"F.W. 펌프 최종 주파수: {self.fw_pump_freq:.1f}Hz")
        logging.info(f"S.W. 펌프 최종 주파수: {self.sw_pump_freq:.1f}Hz")
        
        # 알람 상태 확인
        self.check_alarm_conditions()
        
        # 데이터 로깅
        self.time_data.append(current_time)
        self.t1_data.append(self.T1)
        self.t2_data.append(self.T2)
        self.t4_data.append(self.T4)
        self.t5_data.append(self.T5)
        self.dp1_data.append(self.DP1)
        self.fw_freq_data.append(self.fw_pump_freq)
        self.sw_freq_data.append(self.sw_pump_freq)
        self.fw_count_data.append(self.fw_pump_count)
        self.sw_count_data.append(self.sw_pump_count)
        self.efficiency_data.append(self.heat_exchanger_efficiency)
        self.engine_load_data.append(self.engine_load)
        
        # 데이터 크기 제한 (최근 1000개 포인트만 유지)
        max_data_points = 1000
        if len(self.time_data) > max_data_points:
            self.time_data = self.time_data[-max_data_points:]
            self.t1_data = self.t1_data[-max_data_points:]
            self.t2_data = self.t2_data[-max_data_points:]
            self.t4_data = self.t4_data[-max_data_points:]
            self.t5_data = self.t5_data[-max_data_points:]
            self.dp1_data = self.dp1_data[-max_data_points:]
            self.fw_freq_data = self.fw_freq_data[-max_data_points:]
            self.sw_freq_data = self.sw_freq_data[-max_data_points:]
            self.fw_count_data = self.fw_count_data[-max_data_points:]
            self.sw_count_data = self.sw_count_data[-max_data_points:]
            self.efficiency_data = self.efficiency_data[-max_data_points:]
            self.engine_load_data = self.engine_load_data[-max_data_points:]
        
        # 결과 로깅 (1분마다)
        if int(current_time) % 60 == 0:
            logging.info(f"시스템 상태: T1={self.T1:.1f}°C, T2={self.T2:.1f}°C, T4={self.T4:.1f}°C, T5={self.T5:.1f}°C, DP1={self.DP1:.2f}bar")
            logging.info(f"펌프 상태: F.W.={self.fw_pump_count}대/{self.fw_pump_freq:.1f}Hz, S.W.={self.sw_pump_count}대/{self.sw_pump_freq:.1f}Hz")
            logging.info(f"엔진 부하: {self.engine_load:.1f}%, 열교환기 효율: {self.heat_exchanger_efficiency*100:.0f}%")
        
        return self.T5, self.T2, self.DP1
    
    def run(self):
        """시스템 실행"""
        self.running = True
        update_interval = 0.5  # 0.5초마다 업데이트
        
        logging.info("냉각 시스템 제어 시작")
        
        try:
            while self.running:
                start_time = time.time()
                
                # 시스템 업데이트
                self.update_system()
                
                # 실행 정보 출력
                if len(self.time_data) % 10 == 0:  # 5초마다 로그 출력
                    logging.info(f"상태: T1={self.T1:.2f}°C, T2={self.T2:.2f}°C, "
                                f"T4={self.T4:.2f}°C, T5={self.T5:.2f}°C, DP1={self.DP1:.2f}bar, "
                                f"F.W.={self.fw_pump_freq:.2f}Hz ({self.fw_pump_count}대), "
                                f"S.W.={self.sw_pump_freq:.2f}Hz ({self.sw_pump_count}대)")
                
                # 업데이트 간격 유지
                elapsed = time.time() - start_time
                if elapsed < update_interval:
                    time.sleep(update_interval - elapsed)
        
        except KeyboardInterrupt:
            logging.info("사용자에 의한 시스템 중지")
        except Exception as e:
            logging.error(f"오류 발생: {str(e)}")
        finally:
            self.running = False
            logging.info("냉각 시스템 제어 종료")
    
    def stop(self):
        """시스템 중지"""
        self.running = False
    
    def save_data(self, filename=None):
        """데이터 저장"""
        if not self.time_data:
            logging.warning("저장할 데이터가 없습니다.")
            return False
            
        if filename is None:
            # 현재 시간을 기반으로 파일명 생성
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cooling_data_{current_time}.csv"
            
        try:
            # 데이터 프레임 생성
            data = {
                'Time': [datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S") for t in self.time_data],
                'T1': self.t1_data,
                'T2': self.t2_data,
                'T4': self.t4_data,
                'T5': self.t5_data,
                'DP1': self.dp1_data,
                'FW_Freq': self.fw_freq_data,
                'SW_Freq': self.sw_freq_data,
                'FW_Count': self.fw_count_data,
                'SW_Count': self.sw_count_data,
                'Efficiency': self.efficiency_data,
                'Engine_Load': self.engine_load_data
            }
            
            # CSV 파일로 저장
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                # 헤더 작성
                writer.writerow(data.keys())
                # 데이터 작성
                for i in range(len(self.time_data)):
                    row = [data[key][i] for key in data.keys()]
                    writer.writerow(row)
                    
            logging.info(f"데이터 저장 완료: {filename}")
            return True
            
        except Exception as e:
            logging.error(f"데이터 저장 실패: {str(e)}")
            return False
    
    def manual_update(self, t4, t1, dp1, engine_load):
        """수동 업데이트 - 사용자 입력값 적용"""
        # 입력값 로깅
        logging.info(f"수동 입력: T4={t4:.1f}°C, T1={t1:.1f}°C, DP1={dp1:.2f}bar, 엔진 부하={engine_load:.1f}%")
        
        # 값 업데이트
        self.T4 = t4
        self.T1 = t1
        self.DP1 = dp1
        self.engine_load = engine_load
        
        # 초기 상태 확인 (T5가 T4와 거의 같으면 초기 상태로 간주)
        if abs(self.T5 - self.T4) < 0.1:
            # 초기 상태에서는 T5를 T4보다 2도 낮게 설정
            self.T5 = self.T4 - 2.0
            logging.info(f"초기 상태 감지: T5를 {self.T5:.1f}°C로 설정")
        
        # T2와 T5 계산을 번갈아가며 수행하여 수렴 촉진
        for i in range(3):  # 3회 반복하여 수렴 촉진
            # T2 계산 (S.W. 출구 온도)
            old_t2 = self.T2
            self.calculate_t2()
            
            # T5 계산 (F.W. 출구 온도)
            old_t5 = self.T5
            self.calculate_t5()
            
            # 변화량 로깅
            logging.debug(f"반복 {i+1}: T2 변화={self.T2-old_t2:.2f}°C, T5 변화={self.T5-old_t5:.2f}°C")
            
            # 변화가 미미하면 조기 종료
            if abs(self.T2-old_t2) < 0.01 and abs(self.T5-old_t5) < 0.01:
                break
        
        # 유량 업데이트
        self.update_flow_rates()
        
        # 펌프 주파수 조절 - 사용자 입력 모드에서도 주파수 계산 수행
        self.adjust_fw_pump_frequency()
        self.adjust_sw_pump_frequency()
        
        # 펌프 대수 조정 (엔진 부하 기반)
        self.adjust_pump_count_by_load()
        
        # 알람 상태 확인
        self.check_alarm_conditions()
        
        # 결과 로깅
        logging.info(f"계산 결과: T2={self.T2:.1f}°C, T5={self.T5:.1f}°C, 효율={self.heat_exchanger_efficiency*100:.0f}%")
        logging.info(f"F.W. 펌프 주파수: {self.fw_pump_freq:.1f}Hz, S.W. 펌프 주파수: {self.sw_pump_freq:.1f}Hz")
        
        return self.T5, self.T2, self.DP1

    def adjust_pump_count_by_load(self):
        """엔진 부하에 따라 펌프 대수 조절"""
        # 엔진 부하가 10% 미만이면 펌프 1대만 동작
        if self.engine_load < 10.0:
            if self.fw_pump_count > 1:
                self.fw_pump_count = 1
                logging.info(f"엔진 부하 낮음({self.engine_load:.1f}%): F.W. Pump 대수 감소 (2대 -> 1대)")
            if self.sw_pump_count > 1:
                self.sw_pump_count = 1
                logging.info(f"엔진 부하 낮음({self.engine_load:.1f}%): S.W. Pump 대수 감소 (2대 -> 1대)")
        # 엔진 부하가 10% 이상이면 펌프 2대 동작
        else:
            if self.fw_pump_count < 2:
                self.fw_pump_count = 2
                logging.info(f"엔진 부하 높음({self.engine_load:.1f}%): F.W. Pump 대수 증가 (1대 -> 2대)")
            if self.sw_pump_count < 2:
                self.sw_pump_count = 2
                logging.info(f"엔진 부하 높음({self.engine_load:.1f}%): S.W. Pump 대수 증가 (1대 -> 2대)")
        
        # 펌프 대수에 따른 주파수 조정 - 최대 60Hz로만 제한하고 최소값은 제한하지 않음
        # 주파수 제한만 하고 실제 값은 변경하지 않음 (adjust_fw_pump_frequency 메서드에서 계산된 값 유지)
        if self.fw_pump_freq > 60.0:
            self.fw_pump_freq = 60.0
            logging.info(f"F.W. 펌프 주파수 제한: 60.0Hz로 제한됨")
            
        if self.sw_pump_freq > 60.0:
            self.sw_pump_freq = 60.0
            logging.info(f"S.W. 펌프 주파수 제한: 60.0Hz로 제한됨")


class InputWindow:
    def __init__(self, controller):
        """초기화"""
        self.controller = controller
        self.root = tk.Tk()
        self.root.title("냉각 시스템 제어 UI")
        self.root.geometry("800x700")
        self.root.configure(bg="#333333")
        
        # 변수 초기화 - 체크박스는 삭제했지만 기능은 유지
        self.simulation_var = tk.BooleanVar(value=True)  # 기본값 True로 설정
        self.user_input_var = tk.BooleanVar(value=False)  # 기본값 False로 설정
        self.manual_mode_var = tk.BooleanVar(value=False)  # Manual 모드 변수 추가
        
        # 자동 업데이트 변수 추가
        self.auto_update_active = False
        self.auto_update_interval = 2000  # 2초 (밀리초 단위)
        
        # 컨트롤러에 기본값 설정
        self.controller.simulation_mode = True
        self.controller.user_input_mode = False
        
        # 스타일 설정
        self.setup_styles()
        
        # UI 구성
        self.setup_ui()
        
        # 초기 UI 업데이트
        self.update_ui()
        
        # 입력 필드 비활성화 (초기 상태)
        self.toggle_input_fields(False)
        
        # 실행 버튼 비활성화 (초기 상태)
        self.run_button.config(state="disabled")
        
        # 초기 안내 메시지 설정
        self.guide_label.config(text="데이터를 입력하려면 '데이터 입력' 버튼을 클릭하세요.")
        
        # 업데이트 타이머 설정
        self.root.after(500, self.update_calculated_values)
    
    def setup_styles(self):
        """스타일 설정"""
        self.style = ttk.Style()
        
        # 기본 스타일 설정
        self.style.configure("TLabel", background="#2E2E2E", foreground="white")
        
        # 버튼 스타일 수정 - 텍스트 색상을 검은색으로, 배경색을 노란색으로 변경
        self.style.configure("TButton", background="#FFFF00", foreground="black", font=("Arial", 10, "bold"))
        self.style.map("TButton",
                      foreground=[('pressed', 'black'), ('active', 'black')],
                      background=[('pressed', '#FFD700'), ('active', '#FFFF66')])
        
        self.style.configure("TCheckbutton", background="#2E2E2E", foreground="white")
        self.style.configure("TFrame", background="#2E2E2E")
        self.style.configure("TLabelframe", background="#2E2E2E", foreground="white")
        self.style.configure("TLabelframe.Label", background="#2E2E2E", foreground="white")
        
        # 입력 필드 스타일 설정
        self.style.map('TEntry', 
                  fieldbackground=[('disabled', '#DDDDDD'), ('active', '#FFFF99')])
        
        # 활성화된 입력 필드 스타일
        self.style.configure("Active.TEntry", fieldbackground="#FFFF99")
        
        # 비활성화된 입력 필드 스타일
        self.style.configure("Disabled.TEntry", fieldbackground="#DDDDDD")
        
        # 일반 입력 필드 스타일
        self.style.configure("Normal.TEntry", fieldbackground="white")
    
    def setup_ui(self):
        """UI 구성"""
        # 입력 프레임
        input_frame = ttk.LabelFrame(self.root, text="입력 데이타")
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 모드 선택 프레임
        mode_frame = ttk.Frame(input_frame)
        mode_frame.grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
        
        # Manual 모드 레이블과 버튼
        ttk.Label(mode_frame, text="Manual:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 데이터 입력 버튼 - 커스텀 스타일 적용
        self.input_button = ttk.Button(mode_frame, text="데이터 입력", command=self.enable_manual_input)
        self.input_button.grid(row=0, column=1, padx=5, pady=5)
        
        # 실행 버튼 - 커스텀 스타일 적용
        self.run_button = ttk.Button(mode_frame, text="실행", command=self.run_manual_mode)
        self.run_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Auto 모드 레이블과 버튼
        ttk.Label(mode_frame, text="Auto:", font=("Arial", 10, "bold")).grid(row=0, column=3, sticky=tk.W, padx=15, pady=5)
        
        # 자동 업데이트 버튼 추가 - 커스텀 스타일 적용
        self.auto_update_button = ttk.Button(mode_frame, text="2초 간격 자동 업데이트", command=self.toggle_auto_update)
        self.auto_update_button.grid(row=0, column=4, padx=5, pady=5)
        
        # 구분선
        ttk.Separator(input_frame, orient='horizontal').grid(row=1, column=0, columnspan=4, sticky='ew', pady=5)
        
        # 안내 메시지
        self.guide_label = ttk.Label(input_frame, text="T4(F.W. 입구 온도)와 T1(S.W. 입구 온도)을 입력하세요.", 
                                     foreground="#00FFFF", font=("Arial", 9, "italic"))
        self.guide_label.grid(row=2, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
        
        # 입력 필드와 계산 결과 표시
        # 헤더 (컬럼 제목)
        ttk.Label(input_frame, text="파라미터", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Label(input_frame, text="입력값", font=("Arial", 10, "bold")).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(input_frame, text="계산 결과", font=("Arial", 10, "bold")).grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Label(input_frame, text="단위", font=("Arial", 10, "bold")).grid(row=3, column=3, sticky=tk.W, padx=5, pady=5)
        
        # F.W. Inlet Temp (T4)
        ttk.Label(input_frame, text="F.W. Inlet Temp (T4):", foreground="#FFFF00").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.t4_entry = ttk.Entry(input_frame, width=10, style="Active.TEntry")
        self.t4_entry.grid(row=4, column=1, padx=5, pady=5)
        self.t4_entry.insert(0, f"{self.controller.T4:.1f}")
        # 키 이벤트 바인딩
        self.t4_entry.bind("<Return>", lambda event: self.run_manual_mode())
        self.t4_entry.bind("<FocusOut>", lambda event: None)
        self.t4_entry.bind("<KeyRelease>", lambda event: self.on_key_release(event, "t4"))
        self.t4_result = ttk.Label(input_frame, text=f"{self.controller.T4:.1f}")
        self.t4_result.grid(row=4, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="°C").grid(row=4, column=3, sticky=tk.W, padx=5, pady=5)
        
        # S.W. Inlet Temp (T1)
        ttk.Label(input_frame, text="S.W. Inlet Temp (T1):", foreground="#FFFF00").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.t1_entry = ttk.Entry(input_frame, width=10, style="Active.TEntry")
        self.t1_entry.grid(row=5, column=1, padx=5, pady=5)
        self.t1_entry.insert(0, f"{self.controller.T1:.1f}")
        # 키 이벤트 바인딩
        self.t1_entry.bind("<Return>", lambda event: self.run_manual_mode())
        self.t1_entry.bind("<FocusOut>", lambda event: None)
        self.t1_entry.bind("<KeyRelease>", lambda event: self.on_key_release(event, "t1"))
        self.t1_result = ttk.Label(input_frame, text=f"{self.controller.T1:.1f}")
        self.t1_result.grid(row=5, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="°C").grid(row=5, column=3, sticky=tk.W, padx=5, pady=5)
        
        # S.W. Inlet Pressure (DP1)
        ttk.Label(input_frame, text="S.W. Inlet Pressure (DP1):", foreground="#FFFF00").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        self.dp1_entry = ttk.Entry(input_frame, width=10, style="Active.TEntry")
        self.dp1_entry.grid(row=6, column=1, padx=5, pady=5)
        self.dp1_entry.insert(0, f"{self.controller.DP1:.2f}")
        # 키 이벤트 바인딩
        self.dp1_entry.bind("<Return>", lambda event: self.run_manual_mode())
        self.dp1_entry.bind("<FocusOut>", lambda event: None)
        self.dp1_entry.bind("<KeyRelease>", lambda event: self.on_key_release(event, "dp1"))
        self.dp1_result = ttk.Label(input_frame, text=f"{self.controller.DP1:.2f}")
        self.dp1_result.grid(row=6, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="bar").grid(row=6, column=3, sticky=tk.W, padx=5, pady=5)
        
        # F.W. Outlet Temp (T5) - 추가
        ttk.Label(input_frame, text="F.W. Outlet Temp (T5):", foreground="#00FFFF").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        self.t5_entry = ttk.Entry(input_frame, width=10, style="Disabled.TEntry", state="disabled")
        self.t5_entry.grid(row=7, column=1, padx=5, pady=5)
        self.t5_entry.insert(0, f"{self.controller.T5:.1f}")
        self.t5_result = ttk.Label(input_frame, text=f"{self.controller.T5:.1f}")
        self.t5_result.grid(row=7, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="°C").grid(row=7, column=3, sticky=tk.W, padx=5, pady=5)
        
        # S.W. Outlet Temp (T2) - 추가
        ttk.Label(input_frame, text="S.W. Outlet Temp (T2):", foreground="#00FFFF").grid(row=8, column=0, sticky=tk.W, padx=5, pady=5)
        self.t2_entry = ttk.Entry(input_frame, width=10, style="Disabled.TEntry", state="disabled")
        self.t2_entry.grid(row=8, column=1, padx=5, pady=5)
        self.t2_entry.insert(0, f"{self.controller.T2:.1f}")
        self.t2_result = ttk.Label(input_frame, text=f"{self.controller.T2:.1f}")
        self.t2_result.grid(row=8, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="°C").grid(row=8, column=3, sticky=tk.W, padx=5, pady=5)
        
        # M/E LOAD (엔진 부하)
        ttk.Label(input_frame, text="M/E LOAD:", foreground="#FFFF00").grid(row=9, column=0, sticky=tk.W, padx=5, pady=5)
        self.engine_load_entry = ttk.Entry(input_frame, width=10, style="Active.TEntry")
        self.engine_load_entry.grid(row=9, column=1, padx=5, pady=5)
        self.engine_load_entry.insert(0, f"{self.controller.engine_load:.1f}")
        # 키 이벤트 바인딩
        self.engine_load_entry.bind("<Return>", lambda event: self.run_manual_mode())
        self.engine_load_entry.bind("<FocusOut>", lambda event: None)  # 포커스 아웃 시 아무 동작 안함
        self.engine_load_entry.bind("<KeyRelease>", lambda event: self.on_key_release(event, "engine_load"))
        self.engine_load_result = ttk.Label(input_frame, text=f"{self.controller.engine_load:.1f}")
        self.engine_load_result.grid(row=9, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="%").grid(row=9, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 구분선
        ttk.Separator(input_frame, orient='horizontal').grid(row=10, column=0, columnspan=4, sticky='ew', pady=10)
        
        # 출력 값 표시
        # F.W. Pump 주파수
        ttk.Label(input_frame, text="F.W. Pump 주파수:").grid(row=11, column=0, sticky=tk.W, padx=5, pady=5)
        self.fw_freq_label = ttk.Label(input_frame, text=f"{self.controller.fw_pump_freq:.1f}")
        self.fw_freq_label.grid(row=11, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="Hz").grid(row=11, column=3, sticky=tk.W, padx=5, pady=5)
        
        # F.W. Pump 동작 개수
        ttk.Label(input_frame, text="F.W. Pump 동작 개수:").grid(row=12, column=0, sticky=tk.W, padx=5, pady=5)
        self.fw_count_label = ttk.Label(input_frame, text=f"{self.controller.fw_pump_count}")
        self.fw_count_label.grid(row=12, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="대").grid(row=12, column=3, sticky=tk.W, padx=5, pady=5)
        
        # S.W. Pump 주파수
        ttk.Label(input_frame, text="S.W. Pump 주파수:").grid(row=13, column=0, sticky=tk.W, padx=5, pady=5)
        self.sw_freq_label = ttk.Label(input_frame, text=f"{self.controller.sw_pump_freq:.1f}")
        self.sw_freq_label.grid(row=13, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="Hz").grid(row=13, column=3, sticky=tk.W, padx=5, pady=5)
        
        # S.W. Pump 동작 개수
        ttk.Label(input_frame, text="S.W. Pump 동작 개수:").grid(row=14, column=0, sticky=tk.W, padx=5, pady=5)
        self.sw_count_label = ttk.Label(input_frame, text=f"{self.controller.sw_pump_count}")
        self.sw_count_label.grid(row=14, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="대").grid(row=14, column=3, sticky=tk.W, padx=5, pady=5)
        
        # F.W. 유량
        ttk.Label(input_frame, text="F.W. 유량:").grid(row=15, column=0, sticky=tk.W, padx=5, pady=5)
        self.fw_flow_label = ttk.Label(input_frame, text=f"{self.controller.m_FW:.1f}")
        self.fw_flow_label.grid(row=15, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="m³/h").grid(row=15, column=3, sticky=tk.W, padx=5, pady=5)
        
        # S.W. 유량
        ttk.Label(input_frame, text="S.W. 유량:").grid(row=16, column=0, sticky=tk.W, padx=5, pady=5)
        self.sw_flow_label = ttk.Label(input_frame, text=f"{self.controller.m_SW:.1f}")
        self.sw_flow_label.grid(row=16, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="m³/h").grid(row=16, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 열교환기 효율
        ttk.Label(input_frame, text="열교환기 효율:", foreground="#00FF00").grid(row=17, column=0, sticky=tk.W, padx=5, pady=5)
        self.efficiency_label = ttk.Label(input_frame, text=f"{self.controller.heat_exchanger_efficiency*100:.0f}")
        self.efficiency_label.grid(row=17, column=2, padx=5, pady=5)
        ttk.Label(input_frame, text="%").grid(row=17, column=3, sticky=tk.W, padx=5, pady=5)
        
        # 알람 상태 표시
        self.alarm_label = ttk.Label(input_frame, text="", foreground="red")
        self.alarm_label.grid(row=18, column=0, columnspan=4, padx=5, pady=10)
        
        # 초기 입력 필드 상태 설정
        self.toggle_simulation()  # 시뮬레이션 모드에 따라 입력 필드 상태 설정
    
    def on_key_release(self, event, field_type):
        """키 입력 시 실시간 검증"""
        try:
            if field_type == "t4":
                value = float(self.t4_entry.get())
                # T4는 범위 제한 없음
                self.t4_entry.configure(style="Active.TEntry")
            elif field_type == "t1":
                value = float(self.t1_entry.get())
                if not (0 <= value <= 36):
                    self.t1_entry.configure(style="Error.TEntry")
                else:
                    self.t1_entry.configure(style="Active.TEntry")
            elif field_type == "dp1":
                value = float(self.dp1_entry.get())
                if not (0.1 <= value <= 3.0):
                    self.dp1_entry.configure(style="Error.TEntry")
                else:
                    self.dp1_entry.configure(style="Active.TEntry")
            elif field_type == "engine_load":
                value = float(self.engine_load_entry.get())
                if not (0 <= value <= 100):
                    self.engine_load_entry.configure(style="Error.TEntry")
                else:
                    self.engine_load_entry.configure(style="Active.TEntry")
        except ValueError:
            if field_type == "t4":
                self.t4_entry.configure(style="Error.TEntry")
            elif field_type == "t1":
                self.t1_entry.configure(style="Error.TEntry")
            elif field_type == "dp1":
                self.dp1_entry.configure(style="Error.TEntry")
            elif field_type == "engine_load":
                self.engine_load_entry.configure(style="Error.TEntry")
    
    def update_ui(self):
        """UI 업데이트"""
        # 결과 레이블 업데이트
        self.t5_result.config(text=f"{self.controller.T5:.1f}")
        self.t2_result.config(text=f"{self.controller.T2:.1f}")
        self.dp1_result.config(text=f"{self.controller.DP1:.2f}")
        self.t4_result.config(text=f"{self.controller.T4:.1f}")
        self.t1_result.config(text=f"{self.controller.T1:.1f}")
        self.engine_load_result.config(text=f"{self.controller.engine_load:.1f}")
        
        # 입력 필드 업데이트 (사용자 입력 모드가 아닐 때만)
        if not self.controller.user_input_mode:
            self.t4_entry.delete(0, tk.END)
            self.t4_entry.insert(0, f"{self.controller.T4:.1f}")
            
            self.t1_entry.delete(0, tk.END)
            self.t1_entry.insert(0, f"{self.controller.T1:.1f}")
            
            self.engine_load_entry.delete(0, tk.END)
            self.engine_load_entry.insert(0, f"{self.controller.engine_load:.1f}")
        
        # 계산 결과 필드 업데이트
        self.t5_entry.delete(0, tk.END)
        self.t5_entry.insert(0, f"{self.controller.T5:.1f}")
        
        self.t2_entry.delete(0, tk.END)
        self.t2_entry.insert(0, f"{self.controller.T2:.1f}")
        
        # 펌프 정보 업데이트
        self.fw_freq_label.config(text=f"{self.controller.fw_pump_freq:.1f}")
        self.fw_count_label.config(text=f"{self.controller.fw_pump_count}")
        self.sw_freq_label.config(text=f"{self.controller.sw_pump_freq:.1f}")
        self.sw_count_label.config(text=f"{self.controller.sw_pump_count}")
        
        # 유량 계산 업데이트
        self.controller.update_flow_rates()
        
        # 유량 정보 업데이트
        self.fw_flow_label.config(text=f"{self.controller.m_FW:.1f}")
        self.sw_flow_label.config(text=f"{self.controller.m_SW:.1f}")
        
        # 열교환기 효율 업데이트
        self.efficiency_label.config(text=f"{self.controller.heat_exchanger_efficiency*100:.0f}")
        
        # 알람 상태 업데이트
        if self.controller.alarm_active:
            self.alarm_label.config(text=f"경고: {self.controller.alarm_message}", foreground="red")
        else:
            self.alarm_label.config(text="", foreground="black")
            
        # 입력 필드 상태 업데이트 (시뮬레이션 모드에 따라)
        if self.controller.simulation_mode:
            # 시뮬레이션 모드에서는 계산 결과 필드 비활성화
            self.t5_entry.config(state="disabled")
            self.t2_entry.config(state="disabled")
        else:
            # 수동 모드에서는 계산 결과 필드 활성화
            self.t5_entry.config(state="normal")
            self.t2_entry.config(state="normal")
            
        # 사용자 입력 모드에 따른 입력 필드 상태 설정
        if self.controller.user_input_mode:
            # 사용자 입력 모드에서는 입력 필드 활성화
            self.t4_entry.config(state="normal")
            self.t1_entry.config(state="normal")
            self.dp1_entry.config(state="normal")  # DP1은 항상 사용자 입력 가능
            self.engine_load_entry.config(state="normal")
        else:
            # 시뮬레이션 모드에서는 입력 필드 비활성화 (DP1 제외)
            self.t4_entry.config(state="disabled")
            self.t1_entry.config(state="disabled")
            self.dp1_entry.config(state="normal")  # DP1은 항상 사용자 입력 가능
            self.engine_load_entry.config(state="disabled")
            
        # 업데이트 타이머 재설정
        self.root.after(500, self.update_calculated_values)
    
    def toggle_user_input(self, enable=None):
        """사용자 입력 모드 전환"""
        # 파라미터가 주어지면 해당 값으로 설정, 아니면 현재 값 반전
        if enable is not None:
            self.controller.user_input_mode = enable
            self.user_input_var.set(enable)
        else:
            # 체크박스가 없으므로 변수 값 직접 변경
            self.controller.user_input_mode = not self.controller.user_input_mode
            self.user_input_var.set(self.controller.user_input_mode)
            
        mode_str = "활성화" if self.controller.user_input_mode else "비활성화"
        logging.info(f"사용자 입력 모드 {mode_str}")
        
        # 사용자 입력 모드에 따라 안내 메시지 업데이트
        if self.controller.user_input_mode:
            self.guide_label.config(text="사용자 입력 모드: T4와 T1 값을 직접 입력하세요.", foreground="#FF9900", font=("Arial", 9, "bold"))
            
            # 입력 필드 스타일 변경 (사용자 입력 강조)
            self.t4_entry.config(style="Active.TEntry")
            self.t1_entry.config(style="Active.TEntry")
            
            # 사용자 입력 모드로 전환 시 현재 입력된 값으로 컨트롤러 업데이트
            try:
                t4_value = float(self.t4_entry.get())
                t1_value = float(self.t1_entry.get())
                dp1_value = float(self.dp1_entry.get())
                engine_load_value = float(self.engine_load_entry.get())
                self.controller.manual_update(t4=t4_value, t1=t1_value, dp1=dp1_value, engine_load=engine_load_value)
                logging.info(f"사용자 입력 모드 활성화: T1={t1_value:.2f}°C, T4={t4_value:.2f}°C, DP1={dp1_value:.2f}bar로 고정")
            except ValueError:
                logging.warning("입력값 변환 오류")
        else:
            self.guide_label.config(text="T4(F.W. 입구 온도)와 T1(S.W. 입구 온도)을 입력하세요.", foreground="#00FFFF", font=("Arial", 9, "italic"))
            
            # 입력 필드 스타일 변경 (일반 모드)
            self.t4_entry.config(style="Normal.TEntry")
            self.t1_entry.config(style="Normal.TEntry")
            
            self.toggle_simulation()  # 시뮬레이션 모드에 따라 메시지 업데이트
    
    def toggle_simulation(self, enable=None):
        """시뮬레이션 모드 전환"""
        # 파라미터가 주어지면 해당 값으로 설정, 아니면 현재 값 사용
        if enable is not None:
            self.controller.simulation_mode = enable
            self.simulation_var.set(enable)
        # 체크박스가 없으므로 변수 값은 변경하지 않음
            
        mode_str = "활성화" if self.controller.simulation_mode else "비활성화"
        logging.info(f"시뮬레이션 모드 {mode_str}")
        
        # 사용자 입력 모드가 활성화되어 있지 않을 때만 안내 메시지 업데이트
        if not self.controller.user_input_mode:
            if self.controller.simulation_mode:
                self.guide_label.config(text="시뮬레이션 모드: T4와 T1 값을 입력하면 다른 값들이 자동 계산됩니다.")
            else:
                self.guide_label.config(text="수동 모드: T4와 T1 값을 입력하면 다른 값들이 자동 계산됩니다. 다른 값들도 직접 입력 가능합니다.")
        
        # Manual 모드가 활성화되어 있으면 노란색 파라미터 입력 필드 활성화
        if self.manual_mode_var.get():
            self.t4_entry.config(state="normal")
            self.t1_entry.config(state="normal")
            self.dp1_entry.config(state="normal")
            self.engine_load_entry.config(state="normal")
        else:
            # Manual 모드가 비활성화되어 있으면 시뮬레이션 모드에 따라 설정
            if self.controller.simulation_mode:
                # 시뮬레이션 모드에서는 계산 결과 필드 비활성화
                self.t5_entry.config(state="disabled")
                self.t2_entry.config(state="disabled")
            else:
                # 수동 모드에서는 모든 필드 활성화
                for entry in [self.t5_entry, self.t2_entry]:
                    entry.config(state="normal")
    
    def toggle_auto_update(self):
        """2초 간격 자동 업데이트 토글"""
        self.auto_update_active = not self.auto_update_active
        
        if self.auto_update_active:
            # 자동 업데이트 시작
            self.auto_update_button.config(text="자동 업데이트 중지")
            self.guide_label.config(text="2초 간격으로 T1, T4 값이 자동 업데이트됩니다.", 
                                   foreground="#FF00FF", font=("Arial", 9, "bold"))
            logging.info("2초 간격 자동 업데이트 시작")
            
            # 다른 버튼 비활성화
            self.input_button.config(state="disabled")
            self.run_button.config(state="disabled")
            
            # 첫 번째 업데이트 실행
            self.auto_update()
        else:
            # 자동 업데이트 중지
            self.auto_update_button.config(text="2초 간격 자동 업데이트")
            self.guide_label.config(text="자동 업데이트가 중지되었습니다. 데이터를 입력하려면 '데이터 입력' 버튼을 클릭하세요.", 
                                   foreground="#00FFFF", font=("Arial", 9, "italic"))
            logging.info("2초 간격 자동 업데이트 중지")
            
            # 다른 버튼 활성화
            self.input_button.config(state="normal")
            
            # 입력 필드 비활성화 (초기 상태로 복원)
            self.toggle_input_fields(False)
    
    def auto_update(self):
        """2초 간격으로 T1, T4 값 자동 업데이트"""
        if not self.auto_update_active:
            return
        
        # T1, T4만 랜덤 값 생성
        t1 = RandomDataGenerator.generate_t1_temperature()
        t4 = RandomDataGenerator.generate_t4_temperature()
        
        # 현재 DP1, 엔진 부하 값 유지
        dp1 = self.controller.DP1
        engine_load = self.controller.engine_load
        
        # 생성된 값 로깅
        logging.info(f"자동 업데이트: T1={t1:.1f}°C, T4={t4:.1f}°C")
        
        # 컨트롤러에 값 적용
        self.controller.manual_update(t4=t4, t1=t1, dp1=dp1, engine_load=engine_load)
        
        # 입력 필드 업데이트
        self.t4_entry.delete(0, tk.END)
        self.t4_entry.insert(0, f"{t4:.1f}")
        
        self.t1_entry.delete(0, tk.END)
        self.t1_entry.insert(0, f"{t1:.1f}")
        
        # 결과 업데이트
        self.update_ui()
        
        # 알람 상태 확인 및 업데이트
        self.controller.check_alarm_conditions()
        if self.controller.alarm_active:
            self.alarm_label.config(text=self.controller.alarm_message, foreground="red")
        else:
            self.alarm_label.config(text="정상 상태", foreground="green")
        
        # 강제로 UI 업데이트
        self.root.update_idletasks()
        
        # 다음 업데이트 예약
        self.root.after(self.auto_update_interval, self.auto_update)
    
    def run_manual_mode(self):
        """Manual 모드 실행 - 입력 데이터 적용 및 계산 수행"""
        try:
            # 입력 필드에서 값 가져오기
            t4_input = float(self.t4_entry.get())
            t1_input = float(self.t1_entry.get())
            dp1_input = float(self.dp1_entry.get())
            engine_load_input = float(self.engine_load_entry.get())
            
            # 입력값 범위 검증
            # T4는 범위 제한 없음
            
            if not (0 <= t1_input <= 36):
                messagebox.showwarning("입력 오류", "S.W. 입구 온도(T1)는 0°C에서 36°C 사이여야 합니다.")
                return
            
            if not (0.1 <= dp1_input <= 3.0):
                messagebox.showwarning("입력 오류", "S.W. 입구 차압(DP1)은 0.1bar에서 3.0bar 사이여야 합니다.")
                return
                
            if not (0 <= engine_load_input <= 100):
                messagebox.showwarning("입력 오류", "엔진 부하는 0%에서 100% 사이여야 합니다.")
                return
            
            # 컨트롤러에 값 적용
            self.controller.manual_update(t4=t4_input, t1=t1_input, dp1=dp1_input, engine_load=engine_load_input)
            
            # 입력 필드 비활성화
            self.toggle_input_fields(False)
            
            # UI 업데이트
            self.update_ui()
            
            # 계산된 값 업데이트
            self.update_calculated_values()
            
            # 알람 상태 확인 및 업데이트
            self.controller.check_alarm_conditions()
            if self.controller.alarm_active:
                self.alarm_label.config(text=self.controller.alarm_message, foreground="red")
            else:
                self.alarm_label.config(text="정상 상태", foreground="green")
            
            # 강제로 UI 업데이트
            self.root.update_idletasks()
            
            # 안내 메시지 업데이트
            self.guide_label.config(text="계산이 완료되었습니다. 다시 입력하려면 '데이터 입력' 버튼을 클릭하세요.")
            
            # 실행 버튼 비활성화
            self.run_button.config(state="disabled")
            
            # 완료 메시지 표시
            messagebox.showinfo("실행 완료", "입력한 데이터로 계산이 완료되었습니다.")
            
        except ValueError:
            messagebox.showerror("입력 오류", "모든 입력값은 숫자여야 합니다.")
    
    def get_efficiency_factors(self):
        """효율 계수 계산"""
        # 효율 계수 계산 로직
        return {
            'fw_pump_efficiency': 0.85,
            'sw_pump_efficiency': 0.80,
            'heat_exchanger_efficiency': self.controller.heat_exchanger_efficiency
        }
    
    def update_calculated_values(self):
        """계산된 값 업데이트"""
        # 계산 결과를 UI에 명시적으로 업데이트
        self.t5_result.config(text=f"{self.controller.T5:.1f}")
        self.t2_result.config(text=f"{self.controller.T2:.1f}")
        self.dp1_result.config(text=f"{self.controller.DP1:.2f}")
        self.t4_result.config(text=f"{self.controller.T4:.1f}")
        self.t1_result.config(text=f"{self.controller.T1:.1f}")
        self.engine_load_result.config(text=f"{self.controller.engine_load:.1f}")
        
        # 펌프 정보 업데이트
        self.fw_freq_label.config(text=f"{self.controller.fw_pump_freq:.1f}")
        self.fw_count_label.config(text=f"{self.controller.fw_pump_count}")
        self.sw_freq_label.config(text=f"{self.controller.sw_pump_freq:.1f}")
        self.sw_count_label.config(text=f"{self.controller.sw_pump_count}")
        
        # 유량 정보 업데이트
        self.fw_flow_label.config(text=f"{self.controller.m_FW:.1f}")
        self.sw_flow_label.config(text=f"{self.controller.m_SW:.1f}")
        
        # 열교환기 효율 업데이트
        self.efficiency_label.config(text=f"{self.controller.heat_exchanger_efficiency*100:.0f}")
    
    def toggle_input_fields(self, enable=True):
        """입력 필드 활성화/비활성화"""
        state = "normal" if enable else "disabled"
        
        # 입력 필드 상태 설정
        self.t4_entry.config(state=state)
        self.t1_entry.config(state=state)
        self.dp1_entry.config(state=state)
        self.engine_load_entry.config(state=state)
        
        # 로깅
        logging.info(f"입력 필드 상태 변경: {state}")
        logging.info(f"T4 입력 필드 상태: {self.t4_entry['state']}")
        logging.info(f"T1 입력 필드 상태: {self.t1_entry['state']}")
        logging.info(f"DP1 입력 필드 상태: {self.dp1_entry['state']}")
        logging.info(f"엔진 부하 입력 필드 상태: {self.engine_load_entry['state']}")
    
    def enable_manual_input(self):
        """수동 입력 모드 활성화"""
        # 입력 필드 활성화
        self.toggle_input_fields(True)
        
        # 안내 메시지 업데이트
        self.guide_label.config(text="T4(F.W. 입구 온도), T1(S.W. 입구 온도), DP1(S.W. 입구 압력), 엔진 부하를 입력하세요.")
        
        # 사용자 입력 모드 활성화
        self.toggle_user_input(True)
        
        # 시뮬레이션 모드 비활성화
        self.toggle_simulation(False)
        
        # 실행 버튼 활성화
        self.run_button.config(state="normal")
        
        # 자동 업데이트 중지
        if self.auto_update_active:
            self.toggle_auto_update()
    
    def run_auto_mode(self):
        """Auto 모드 실행 (랜덤 데이터 생성)"""
        # 입력 필드 활성화
        self.toggle_input_fields(True)
        
        # T1, T4만 랜덤 값 생성
        t1 = RandomDataGenerator.generate_t1_temperature()
        t4 = RandomDataGenerator.generate_t4_temperature()
        
        # 현재 DP1, 엔진 부하 값 유지
        dp1 = self.controller.DP1
        engine_load = self.controller.engine_load
        
        # 생성된 값 로깅
        logging.info(f"랜덤 데이터 생성: T1={t1:.1f}°C, T4={t4:.1f}°C")
        
        # 입력 필드에 랜덤 값 설정
        self.t4_entry.delete(0, tk.END)
        self.t4_entry.insert(0, f"{t4:.1f}")
        
        self.t1_entry.delete(0, tk.END)
        self.t1_entry.insert(0, f"{t1:.1f}")
        
        # 계산 실행
        self.controller.manual_update(t4=t4, t1=t1, dp1=dp1, engine_load=engine_load)
        
        # 계산 결과를 UI에 명시적으로 업데이트
        self.t5_result.config(text=f"{self.controller.T5:.1f}")
        self.t2_result.config(text=f"{self.controller.T2:.1f}")
        self.dp1_result.config(text=f"{self.controller.DP1:.2f}")
        self.t4_result.config(text=f"{self.controller.T4:.1f}")
        self.t1_result.config(text=f"{self.controller.T1:.1f}")
        self.engine_load_result.config(text=f"{self.controller.engine_load:.1f}")
        
        # 펌프 정보 업데이트
        self.fw_freq_label.config(text=f"{self.controller.fw_pump_freq:.1f}")
        self.fw_count_label.config(text=f"{self.controller.fw_pump_count}")
        self.sw_freq_label.config(text=f"{self.controller.sw_pump_freq:.1f}")
        self.sw_count_label.config(text=f"{self.controller.sw_pump_count}")
        
        # 유량 정보 업데이트
        self.fw_flow_label.config(text=f"{self.controller.m_FW:.1f}")
        self.sw_flow_label.config(text=f"{self.controller.m_SW:.1f}")
        
        # 열교환기 효율 업데이트
        self.efficiency_label.config(text=f"{self.controller.heat_exchanger_efficiency*100:.0f}")
        
        # 알람 상태 업데이트
        if self.controller.alarm_active:
            self.alarm_label.config(text=f"경고: {self.controller.alarm_message}", foreground="red")
        else:
            self.alarm_label.config(text="", foreground="black")
        
        # UI 강제 업데이트
        self.root.update_idletasks()
        
        # 입력 필드 비활성화
        self.toggle_input_fields(False)
        
        # 안내 메시지 업데이트
        self.guide_label.config(text="자동 입력이 완료되었습니다. 다시 입력하려면 '데이터 입력' 버튼을 클릭하세요.")
        
        # 완료 메시지 표시
        messagebox.showinfo("자동 입력 완료", f"랜덤 데이터가 생성되었습니다.\nT1(해수 입구)={t1:.1f}°C\nT4(담수 입구)={t4:.1f}°C")


def main():
    """메인 함수"""
    # 컨트롤러 생성
    controller = CoolingSystemController()
    
    # UI 생성
    ui = InputWindow(controller)
    
    # 컨트롤러 스레드 시작
    controller_thread = threading.Thread(target=controller.run)
    controller_thread.daemon = True
    controller_thread.start()
    
    try:
        # UI 시작
        ui.root.mainloop()
    except KeyboardInterrupt:
        print("프로그램 종료 중...")
    finally:
        # 컨트롤러 중지
        controller.stop()
        # 데이터 저장
        controller.save_data()
        print("프로그램이 종료되었습니다.")


if __name__ == "__main__":
    main()
