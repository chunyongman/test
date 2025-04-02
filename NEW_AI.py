import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cooling_system.log"),
        logging.StreamHandler()
    ]
)

class CoolingSystemController:
    def __init__(self):
        # 초기 온도 및 유량 설정
        self.T1 = 25.0  # S.W. Inlet Temperature (°C)
        self.T2 = 30.0  # S.W. Outlet Temperature (°C)
        self.T4 = 38.0  # F.W. Inlet Temperature (°C)
        self.T5 = 36.0  # F.W. Outlet Temperature (°C)
        
        # 초기 유량 설정 (m³/h)
        self.m_FW = 100.0  # Fresh Water 유량
        self.m_SW = 120.0  # Sea Water 유량
        
        # 초기 펌프 주파수 설정 (Hz)
        self.fw_pump_freq = 60.0  # F.W. Pump 주파수
        self.sw_pump_freq = 60.0  # S.W. Pump 주파수
        
        # 주파수 제한 설정
        self.fw_pump_min_freq = 40.0
        self.fw_pump_max_freq = 60.0
        self.sw_pump_min_freq = 35.0
        self.sw_pump_max_freq = 60.0
        
        # 주파수 변화율 제한 (Hz/s)
        self.max_freq_change_rate = 0.5
        
        # PID 제어 파라미터
        self.fw_pid = {
            'P': 1.5,
            'I': 0.05,
            'D': 0.02,
            'prev_error': 0,
            'integral': 0,
            'last_time': time.time()
        }
        
        # 데이터 로깅을 위한 리스트
        self.time_data = []
        self.t1_data = []
        self.t2_data = []
        self.t4_data = []
        self.t5_data = []
        self.fw_freq_data = []
        self.sw_freq_data = []
        
        # 알람 상태
        self.alarm_active = False
        
        # 시뮬레이션 모드 설정
        self.simulation_mode = True
        
        # 시스템 상태
        self.running = False
        
        logging.info("냉각 시스템 컨트롤러 초기화 완료")
    
    def calculate_t5(self):
        """F.W. Outlet Temperature (T5) 계산"""
        # T5 = T4 - (mSW/mFW) * (T2-T1)
        if self.m_FW > 0:
            self.T5 = self.T4 - (self.m_SW / self.m_FW) * (self.T2 - self.T1)
        else:
            logging.warning("F.W. 유량이 0이하입니다. T5 계산 불가")
            self.T5 = self.T4  # 기본값 유지
        return self.T5
    
    def update_flow_rates(self):
        """펌프 주파수에 따른 유량 업데이트"""
        # 주파수와 유량 간의 관계 (선형 관계로 가정)
        # 실제 시스템에서는 펌프 특성 곡선에 따라 더 복잡한 관계식 사용 필요
        self.m_FW = 100.0 * (self.fw_pump_freq / 60.0) ** 2
        self.m_SW = 120.0 * (self.sw_pump_freq / 60.0) ** 2
    
    def adjust_fw_pump_frequency(self):
        """F.W. Pump 주파수 조절 로직"""
        target_temp = 36.0  # 목표 온도
        delta_T = self.T4 - target_temp
        
        # PID 제어 적용
        current_time = time.time()
        dt = current_time - self.fw_pid['last_time']
        
        if dt > 0:
            # 비례항
            p_term = self.fw_pid['P'] * delta_T
            
            # 적분항
            self.fw_pid['integral'] += delta_T * dt
            i_term = self.fw_pid['I'] * self.fw_pid['integral']
            
            # 미분항
            d_term = 0
            if dt > 0:
                d_term = self.fw_pid['D'] * (delta_T - self.fw_pid['prev_error']) / dt
            
            # PID 출력 계산
            output = p_term + i_term + d_term
            
            # 주파수 변화율 제한
            max_change = self.max_freq_change_rate * dt
            output = np.clip(output, -max_change, max_change)
            
            # 새 주파수 계산 및 제한
            new_freq = self.fw_pump_freq + output
            new_freq = np.clip(new_freq, self.fw_pump_min_freq, self.fw_pump_max_freq)
            
            # 주파수 업데이트
            if abs(new_freq - self.fw_pump_freq) > 0.01:  # 미세 변화 무시
                old_freq = self.fw_pump_freq
                self.fw_pump_freq = new_freq
                logging.info(f"F.W. Pump 주파수 변경: {old_freq:.2f}Hz -> {new_freq:.2f}Hz (ΔT: {delta_T:.2f}°C)")
            
            # PID 상태 업데이트
            self.fw_pid['prev_error'] = delta_T
            self.fw_pid['last_time'] = current_time
    
    def adjust_sw_pump_frequency(self):
        """S.W. Pump 주파수 조절 로직"""
        current_time = time.time()
        dt = current_time - self.fw_pid['last_time']  # 같은 타임스탬프 사용
        
        # T5 기반 주파수 조절
        if self.T5 > 36.0:
            # T5가 너무 높으면 주파수 증가
            change = self.max_freq_change_rate * dt
            new_freq = self.sw_pump_freq + change
        elif self.T5 < 34.0:
            # T5가 너무 낮으면 주파수 감소
            change = -self.max_freq_change_rate * dt
            new_freq = self.sw_pump_freq + change
        else:
            # 34°C ~ 36°C 구간에서는 현재 주파수 유지
            new_freq = self.sw_pump_freq
        
        # 주파수 제한
        new_freq = np.clip(new_freq, self.sw_pump_min_freq, self.sw_pump_max_freq)
        
        # 주파수 업데이트
        if abs(new_freq - self.sw_pump_freq) > 0.01:  # 미세 변화 무시
            old_freq = self.sw_pump_freq
            self.sw_pump_freq = new_freq
            logging.info(f"S.W. Pump 주파수 변경: {old_freq:.2f}Hz -> {new_freq:.2f}Hz (T5: {self.T5:.2f}°C)")
    
    def check_alarms(self):
        """비상 보호 로직 및 알람 체크"""
        # 급격한 온도 변화 감지 (5초 내 3도 변화)
        if len(self.t4_data) > 5:
            time_window = 5  # 5초
            if len(self.time_data) >= 2 and (self.time_data[-1] - self.time_data[-time_window]) <= 5:
                temp_change = abs(self.t4_data[-1] - self.t4_data[-time_window])
                if temp_change >= 3.0:
                    if not self.alarm_active:
                        logging.warning(f"알람: 급격한 온도 변화 감지! {time_window}초 내 {temp_change:.2f}°C 변화")
                        self.alarm_active = True
                    # 주파수 변화 제한 강화
                    self.max_freq_change_rate = 0.2  # 더 느린 변화율로 제한
                else:
                    if self.alarm_active:
                        logging.info("알람 해제: 온도 변화 정상")
                        self.alarm_active = False
                    self.max_freq_change_rate = 0.5  # 정상 변화율로 복귀
        
        # 센서 오류 감지 (비정상적인 값)
        if (self.T1 < 0 or self.T1 > 50 or 
            self.T2 < 0 or self.T2 > 60 or 
            self.T4 < 0 or self.T4 > 70 or 
            self.T5 < 0 or self.T5 > 70):
            logging.error("알람: 센서 오류 감지! 비정상적인 온도 값")
            # 기본 주파수로 설정
            self.fw_pump_freq = 45.0
            self.sw_pump_freq = 45.0
    
    def simulate_temperature_changes(self):
        """시뮬레이션 모드에서 온도 변화 시뮬레이션"""
        if not self.simulation_mode:
            return
        
        # 엔진 부하 변화에 따른 T4 변화 시뮬레이션
        time_of_day = (time.time() % 86400) / 3600  # 하루 중 시간 (0-24)
        
        # 부하 패턴 시뮬레이션 (시간에 따른 사인파 + 랜덤 노이즈)
        load_factor = 0.5 + 0.3 * np.sin(2 * np.pi * time_of_day / 12) + 0.1 * np.random.randn()
        load_factor = np.clip(load_factor, 0.2, 1.0)
        
        # T4 변화 (엔진 부하에 따라)
        target_t4 = 32 + 10 * load_factor  # 32°C ~ 42°C 범위
        self.T4 += (target_t4 - self.T4) * 0.05  # 천천히 변화
        
        # T1 (해수 온도) 변화 시뮬레이션
        target_t1 = 22 + 5 * np.sin(2 * np.pi * time_of_day / 24) + 0.5 * np.random.randn()
        self.T1 += (target_t1 - self.T1) * 0.02  # 매우 천천히 변화
        
        # 열교환 효과 시뮬레이션
        # T2 = T1 + 열전달량/해수유량
        heat_transfer = self.m_FW * (self.T4 - self.T5)  # 담수 측 열전달
        if self.m_SW > 0:
            self.T2 = self.T1 + heat_transfer / self.m_SW
        else:
            self.T2 = self.T1
    
    def update_system(self):
        """시스템 상태 업데이트"""
        # 유량 업데이트
        self.update_flow_rates()
        
        # 시뮬레이션 모드에서 온도 변화
        self.simulate_temperature_changes()
        
        # T5 계산
        self.calculate_t5()
        
        # 펌프 주파수 조절
        self.adjust_fw_pump_frequency()
        self.adjust_sw_pump_frequency()
        
        # 알람 체크
        self.check_alarms()
        
        # 데이터 로깅
        current_time = time.time()
        self.time_data.append(current_time)
        self.t1_data.append(self.T1)
        self.t2_data.append(self.T2)
        self.t4_data.append(self.T4)
        self.t5_data.append(self.T5)
        self.fw_freq_data.append(self.fw_pump_freq)
        self.sw_freq_data.append(self.sw_pump_freq)
        
        # 데이터 크기 제한 (최근 1000개 포인트만 유지)
        max_data_points = 1000
        if len(self.time_data) > max_data_points:
            self.time_data = self.time_data[-max_data_points:]
            self.t1_data = self.t1_data[-max_data_points:]
            self.t2_data = self.t2_data[-max_data_points:]
            self.t4_data = self.t4_data[-max_data_points:]
            self.t5_data = self.t5_data[-max_data_points:]
            self.fw_freq_data = self.fw_freq_data[-max_data_points:]
            self.sw_freq_data = self.sw_freq_data[-max_data_points:]
    
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
                                f"T4={self.T4:.2f}°C, T5={self.T5:.2f}°C, "
                                f"F.W.={self.fw_pump_freq:.2f}Hz, S.W.={self.sw_pump_freq:.2f}Hz")
                
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
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cooling_data_{timestamp}.csv"
        
        try:
            with open(filename, 'w') as f:
                f.write("Time,T1,T2,T4,T5,FW_Freq,SW_Freq\n")
                start_time = self.time_data[0] if self.time_data else 0
                for i in range(len(self.time_data)):
                    f.write(f"{self.time_data[i]-start_time:.2f},{self.t1_data[i]:.2f},"
                            f"{self.t2_data[i]:.2f},{self.t4_data[i]:.2f},{self.t5_data[i]:.2f},"
                            f"{self.fw_freq_data[i]:.2f},{self.sw_freq_data[i]:.2f}\n")
            logging.info(f"데이터 저장 완료: {filename}")
            return True
        except Exception as e:
            logging.error(f"데이터 저장 실패: {str(e)}")
            return False


class CoolingSystemUI:
    def __init__(self, controller):
        self.controller = controller
        self.fig = None
        self.animation = None
    
    def start_ui(self):
        """UI 시작"""
        plt.style.use('dark_background')
        self.fig = plt.figure(figsize=(14, 8))
        self.fig.canvas.manager.set_window_title('선박 중앙 냉각 시스템 모니터링')
        
        # 그래프 레이아웃 설정
        gs = self.fig.add_gridspec(3, 2)
        
        # 온도 그래프
        self.ax1 = self.fig.add_subplot(gs[0, :])
        self.ax1.set_title('온도 모니터링')
        self.ax1.set_ylabel('온도 (°C)')
        self.ax1.grid(True, linestyle='--', alpha=0.7)
        
        # 주파수 그래프
        self.ax2 = self.fig.add_subplot(gs[1, :])
        self.ax2.set_title('펌프 주파수')
        self.ax2.set_ylabel('주파수 (Hz)')
        self.ax2.grid(True, linestyle='--', alpha=0.7)
        
        # 유량 그래프
        self.ax3 = self.fig.add_subplot(gs[2, 0])
        self.ax3.set_title('유량')
        self.ax3.set_ylabel('유량 (m³/h)')
        self.ax3.grid(True, linestyle='--', alpha=0.7)
        
        # 시스템 상태 표시
        self.ax4 = self.fig.add_subplot(gs[2, 1])
        self.ax4.set_title('시스템 상태')
        self.ax4.axis('off')
        
        # 그래프 업데이트 함수
        def update(frame):
            # 데이터가 없으면 업데이트 건너뛰기
            if not self.controller.time_data:
                return
            
            # 시간 데이터 변환 (상대 시간)
            rel_time = [t - self.controller.time_data[0] for t in self.controller.time_data]
            
            # 온도 그래프 업데이트
            self.ax1.clear()
            self.ax1.plot(rel_time, self.controller.t1_data, 'b-', label='T1 (S.W. Inlet)')
            self.ax1.plot(rel_time, self.controller.t2_data, 'c-', label='T2 (S.W. Outlet)')
            self.ax1.plot(rel_time, self.controller.t4_data, 'r-', label='T4 (F.W. Inlet)')
            self.ax1.plot(rel_time, self.controller.t5_data, 'm-', label='T5 (F.W. Outlet)')
            self.ax1.axhline(y=36, color='y', linestyle='--', alpha=0.5, label='목표 온도')
            self.ax1.set_title('온도 모니터링')
            self.ax1.set_ylabel('온도 (°C)')
            self.ax1.grid(True, linestyle='--', alpha=0.7)
            self.ax1.legend(loc='upper right')
            
            # 주파수 그래프 업데이트
            self.ax2.clear()
            self.ax2.plot(rel_time, self.controller.fw_freq_data, 'g-', label='F.W. Pump')
            self.ax2.plot(rel_time, self.controller.sw_freq_data, 'y-', label='S.W. Pump')
            self.ax2.set_title('펌프 주파수')
            self.ax2.set_ylabel('주파수 (Hz)')
            self.ax2.set_ylim(30, 65)
            self.ax2.grid(True, linestyle='--', alpha=0.7)
            self.ax2.legend(loc='upper right')
            
            # 유량 그래프 업데이트
            self.ax3.clear()
            # 주파수에 따른 유량 계산 (컨트롤러의 공식 사용)
            fw_flow = [100.0 * (f / 60.0) ** 2 for f in self.controller.fw_freq_data]
            sw_flow = [120.0 * (f / 60.0) ** 2 for f in self.controller.sw_freq_data]
            self.ax3.plot(rel_time, fw_flow, 'g-', label='F.W. 유량')
            self.ax3.plot(rel_time, sw_flow, 'y-', label='S.W. 유량')
            self.ax3.set_title('유량')
            self.ax3.set_ylabel('유량 (m³/h)')
            self.ax3.grid(True, linestyle='--', alpha=0.7)
            self.ax3.legend(loc='upper right')
            
            # 시스템 상태 표시 업데이트
            self.ax4.clear()
            self.ax4.axis('off')
            status_text = [
                f"현재 상태:",
                f"T1 (S.W. Inlet): {self.controller.T1:.2f}°C",
                f"T2 (S.W. Outlet): {self.controller.T2:.2f}°C",
                f"T4 (F.W. Inlet): {self.controller.T4:.2f}°C",
                f"T5 (F.W. Outlet): {self.controller.T5:.2f}°C",
                f"F.W. Pump: {self.controller.fw_pump_freq:.2f}Hz",
                f"S.W. Pump: {self.controller.sw_pump_freq:.2f}Hz",
                f"F.W. 유량: {self.controller.m_FW:.2f}m³/h",
                f"S.W. 유량: {self.controller.m_SW:.2f}m³/h",
            ]
            
            # 알람 상태 표시
            if self.controller.alarm_active:
                status_text.append("\n⚠️ 알람 활성화: 급격한 온도 변화 감지!")
            
            self.ax4.text(0.05, 0.95, '\n'.join(status_text), 
                         transform=self.ax4.transAxes, fontsize=10, 
                         verticalalignment='top', bbox=dict(boxstyle='round', 
                                                          facecolor='black', 
                                                          alpha=0.2))
            
            # x축 레이블 (마지막 그래프에만)
            self.ax3.set_xlabel('시간 (초)')
            
            # 그래프 레이아웃 조정
            plt.tight_layout()
        
        # 애니메이션 시작
        self.animation = FuncAnimation(self.fig, update, interval=1000, cache_frame_data=False)
        plt.tight_layout()
        plt.show()


def main():
    """메인 함수"""
    # 컨트롤러 생성
    controller = CoolingSystemController()
    
    # UI 생성
    ui = CoolingSystemUI(controller)
    
    # 컨트롤러 스레드 시작
    controller_thread = threading.Thread(target=controller.run)
    controller_thread.daemon = True
    controller_thread.start()
    
    try:
        # UI 시작
        ui.start_ui()
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
