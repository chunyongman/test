import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import logging

class PumpOptimizer:
    def __init__(self):
        """펌프 최적화 AI 모듈 초기화"""
        self.fw_model = None
        self.sw_model = None
        self.scaler_X = None
        self.scaler_y = None
        self.is_trained = False
        self.training_data = {
            'T1': [],
            'T2': [],
            'T4': [],
            'T5': [],
            'm_FW': [],
            'm_SW': [],
            'fw_freq': [],
            'sw_freq': []
        }
        
        logging.info("AI 펌프 최적화 모듈 초기화 완료")
    
    def add_training_data(self, T1, T2, T4, T5, m_FW, m_SW, fw_freq, sw_freq):
        """학습 데이터 추가"""
        self.training_data['T1'].append(T1)
        self.training_data['T2'].append(T2)
        self.training_data['T4'].append(T4)
        self.training_data['T5'].append(T5)
        self.training_data['m_FW'].append(m_FW)
        self.training_data['m_SW'].append(m_SW)
        self.training_data['fw_freq'].append(fw_freq)
        self.training_data['sw_freq'].append(sw_freq)
    
    def train_models(self):
        """모델 학습"""
        if len(self.training_data['T1']) < 100:
            logging.warning("학습 데이터가 부족합니다. 최소 100개 이상의 데이터가 필요합니다.")
            return False
        
        try:
            # 데이터 준비
            df = pd.DataFrame(self.training_data)
            
            # 특성 및 타겟 분리
            X = df[['T1', 'T2', 'T4', 'T5', 'm_FW', 'm_SW']].values
            y_fw = df['fw_freq'].values
            y_sw = df['sw_freq'].values
            
            # 데이터 스케일링
            self.scaler_X = StandardScaler()
            X_scaled = self.scaler_X.fit_transform(X)
            
            # F.W. Pump 모델 학습
            self.fw_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.fw_model.fit(X_scaled, y_fw)
            
            # S.W. Pump 모델 학습
            self.sw_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.sw_model.fit(X_scaled, y_sw)
            
            self.is_trained = True
            logging.info("AI 모델 학습 완료")
            return True
            
        except Exception as e:
            logging.error(f"모델 학습 중 오류 발생: {str(e)}")
            return False
    
    def predict_optimal_frequencies(self, T1, T2, T4, T5, m_FW, m_SW):
        """최적 주파수 예측"""
        if not self.is_trained:
            logging.warning("모델이 학습되지 않았습니다. 기본값을 반환합니다.")
            return 60.0, 60.0
        
        try:
            # 입력 데이터 준비
            X = np.array([[T1, T2, T4, T5, m_FW, m_SW]])
            X_scaled = self.scaler_X.transform(X)
            
            # 예측
            fw_freq = self.fw_model.predict(X_scaled)[0]
            sw_freq = self.sw_model.predict(X_scaled)[0]
            
            # 주파수 범위 제한
            fw_freq = np.clip(fw_freq, 40.0, 60.0)
            sw_freq = np.clip(sw_freq, 35.0, 60.0)
            
            return fw_freq, sw_freq
            
        except Exception as e:
            logging.error(f"예측 중 오류 발생: {str(e)}")
            return 60.0, 60.0
    
    def save_models(self, fw_model_path='fw_pump_model.pkl', sw_model_path='sw_pump_model.pkl'):
        """모델 저장"""
        if not self.is_trained:
            logging.warning("학습된 모델이 없어 저장할 수 없습니다.")
            return False
        
        try:
            # 모델 저장
            joblib.dump(self.fw_model, fw_model_path)
            joblib.dump(self.sw_model, sw_model_path)
            
            # 스케일러 저장
            joblib.dump(self.scaler_X, 'scaler_X.pkl')
            
            logging.info(f"모델 저장 완료: {fw_model_path}, {sw_model_path}")
            return True
            
        except Exception as e:
            logging.error(f"모델 저장 중 오류 발생: {str(e)}")
            return False
    
    def load_models(self, fw_model_path='fw_pump_model.pkl', sw_model_path='sw_pump_model.pkl'):
        """모델 로드"""
        try:
            # 모델 로드
            self.fw_model = joblib.load(fw_model_path)
            self.sw_model = joblib.load(sw_model_path)
            
            # 스케일러 로드
            self.scaler_X = joblib.load('scaler_X.pkl')
            
            self.is_trained = True
            logging.info(f"모델 로드 완료: {fw_model_path}, {sw_model_path}")
            return True
            
        except Exception as e:
            logging.error(f"모델 로드 중 오류 발생: {str(e)}")
            return False
    
    def evaluate_model_performance(self, test_data=None):
        """모델 성능 평가"""
        if not self.is_trained:
            logging.warning("학습된 모델이 없어 평가할 수 없습니다.")
            return None
        
        try:
            # 테스트 데이터가 없으면 학습 데이터의 20%를 테스트 데이터로 사용
            if test_data is None:
                df = pd.DataFrame(self.training_data)
                test_size = int(len(df) * 0.2)
                test_df = df.sample(n=test_size, random_state=42)
                
                X_test = test_df[['T1', 'T2', 'T4', 'T5', 'm_FW', 'm_SW']].values
                y_test_fw = test_df['fw_freq'].values
                y_test_sw = test_df['sw_freq'].values
            else:
                X_test = test_data[['T1', 'T2', 'T4', 'T5', 'm_FW', 'm_SW']].values
                y_test_fw = test_data['fw_freq'].values
                y_test_sw = test_data['sw_freq'].values
            
            # 데이터 스케일링
            X_test_scaled = self.scaler_X.transform(X_test)
            
            # 예측
            y_pred_fw = self.fw_model.predict(X_test_scaled)
            y_pred_sw = self.sw_model.predict(X_test_scaled)
            
            # 평균 제곱 오차 계산
            mse_fw = np.mean((y_test_fw - y_pred_fw) ** 2)
            mse_sw = np.mean((y_test_sw - y_pred_sw) ** 2)
            
            # 평균 절대 오차 계산
            mae_fw = np.mean(np.abs(y_test_fw - y_pred_fw))
            mae_sw = np.mean(np.abs(y_test_sw - y_pred_sw))
            
            results = {
                'fw_pump': {
                    'mse': mse_fw,
                    'mae': mae_fw,
                    'rmse': np.sqrt(mse_fw)
                },
                'sw_pump': {
                    'mse': mse_sw,
                    'mae': mae_sw,
                    'rmse': np.sqrt(mse_sw)
                }
            }
            
            logging.info(f"모델 평가 결과: F.W. Pump RMSE={results['fw_pump']['rmse']:.4f}, S.W. Pump RMSE={results['sw_pump']['rmse']:.4f}")
            return results
            
        except Exception as e:
            logging.error(f"모델 평가 중 오류 발생: {str(e)}")
            return None


# 사용 예시
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 최적화 모듈 초기화
    optimizer = PumpOptimizer()
    
    # 샘플 데이터 생성
    np.random.seed(42)
    for _ in range(200):
        T1 = np.random.uniform(20, 30)
        T2 = T1 + np.random.uniform(3, 8)
        T4 = np.random.uniform(32, 42)
        T5 = T4 - np.random.uniform(2, 6)
        m_FW = np.random.uniform(80, 120)
        m_SW = np.random.uniform(100, 140)
        
        # 이상적인 주파수 계산 (시뮬레이션)
        fw_freq = 40 + 20 * (T4 - 32) / 10  # T4가 32~42일 때 40~60Hz
        sw_freq = 35 + 25 * (T5 - 30) / 10  # T5가 30~40일 때 35~60Hz
        
        # 약간의 노이즈 추가
        fw_freq += np.random.normal(0, 1)
        sw_freq += np.random.normal(0, 1)
        
        # 범위 제한
        fw_freq = np.clip(fw_freq, 40, 60)
        sw_freq = np.clip(sw_freq, 35, 60)
        
        # 학습 데이터 추가
        optimizer.add_training_data(T1, T2, T4, T5, m_FW, m_SW, fw_freq, sw_freq)
    
    # 모델 학습
    optimizer.train_models()
    
    # 모델 평가
    results = optimizer.evaluate_model_performance()
    
    # 새로운 데이터에 대한 예측
    T1 = 25.0
    T2 = 30.0
    T4 = 38.0
    T5 = 36.0
    m_FW = 100.0
    m_SW = 120.0
    
    fw_freq, sw_freq = optimizer.predict_optimal_frequencies(T1, T2, T4, T5, m_FW, m_SW)
    print(f"예측된 최적 주파수: F.W. Pump = {fw_freq:.2f}Hz, S.W. Pump = {sw_freq:.2f}Hz")
    
    # 모델 저장
    optimizer.save_models() 