#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pickle
import datetime
from typing import Dict, List, Optional, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Googleカレンダーのスコープ設定
SCOPES = ['https://www.googleapis.com/auth/calendar']


class CalendarClient:
    """Google Calendar APIクライアントクラス"""

    def __init__(self):
        self.service = None
        self.credentials_file = "config/credentials.json"
        self.token_file = "config/token.pickle"
        self._authenticate()

    def _authenticate(self) -> None:
        """Google Calendar APIの認証処理"""
        creds = None
        
        # token.pickleファイルから既存の認証情報を読み込み
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # 認証情報が無効または期限切れの場合、再認証
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"{self.credentials_file}が見つかりません。"
                        "Google Cloud Consoleから認証情報をダウンロードしてください。"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # 認証情報を保存
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        # Calendar APIサービスの初期化
        self.service = build('calendar', 'v3', credentials=creds)

    def create_event(self, summary: str, start_datetime: str, 
                    end_datetime: Optional[str] = None, 
                    description: str = "", 
                    calendar_id: str = 'primary') -> Optional[str]:
        """
        Googleカレンダーにイベントを作成
        
        Args:
            summary: イベントのタイトル
            start_datetime: 開始日時（ISO 8601フォーマット）
            end_datetime: 終了日時（指定なしの場合は1時間後）
            description: イベントの説明
            calendar_id: カレンダーID（デフォルトはprimary）
            
        Returns:
            作成されたイベントのID（失敗時はNone）
        """
        try:
            # 終了時刻が指定されていない場合は1時間後に設定
            if not end_datetime:
                start_dt = datetime.datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                end_dt = start_dt + datetime.timedelta(hours=1)
                end_datetime = end_dt.isoformat()

            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_datetime,
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': end_datetime,
                    'timeZone': 'Asia/Tokyo',
                },
            }

            event_result = self.service.events().insert(
                calendarId=calendar_id, body=event).execute()
            
            print(f"イベントが作成されました: {event_result.get('htmlLink')}")
            return event_result['id']
            
        except HttpError as error:
            print(f"Googleカレンダーイベント作成エラー: {error}")
            return None
        except Exception as error:
            print(f"イベント作成エラー: {error}")
            return None

    def search_events(self, query: str = "", 
                     time_min: Optional[str] = None,
                     time_max: Optional[str] = None, 
                     max_results: int = 10,
                     calendar_id: str = 'primary') -> List[Dict[str, Any]]:
        """
        Googleカレンダーからイベントを検索
        
        Args:
            query: 検索クエリ
            time_min: 検索開始時刻（ISO 8601フォーマット）
            time_max: 検索終了時刻（ISO 8601フォーマット）
            max_results: 最大取得件数
            calendar_id: カレンダーID
            
        Returns:
            イベントのリスト
        """
        try:
            # デフォルトで現在時刻から30日間を検索
            if not time_min:
                time_min = datetime.datetime.utcnow().isoformat() + 'Z'
            if not time_max:
                max_date = datetime.datetime.utcnow() + datetime.timedelta(days=30)
                time_max = max_date.isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
                q=query
            ).execute()

            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                formatted_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', '（タイトルなし）'),
                    'start': start,
                    'description': event.get('description', ''),
                    'link': event.get('htmlLink', '')
                })
            
            return formatted_events
            
        except HttpError as error:
            print(f"Googleカレンダーイベント検索エラー: {error}")
            return []
        except Exception as error:
            print(f"イベント検索エラー: {error}")
            return []

    def update_event(self, event_id: str, summary: Optional[str] = None,
                    start_datetime: Optional[str] = None,
                    end_datetime: Optional[str] = None,
                    description: Optional[str] = None,
                    calendar_id: str = 'primary') -> bool:
        """
        既存のイベントを更新
        
        Args:
            event_id: 更新するイベントのID
            summary: 新しいタイトル
            start_datetime: 新しい開始日時
            end_datetime: 新しい終了日時
            description: 新しい説明
            calendar_id: カレンダーID
            
        Returns:
            更新成功時True、失敗時False
        """
        try:
            # 既存のイベントを取得
            event = self.service.events().get(
                calendarId=calendar_id, eventId=event_id).execute()

            # 指定されたフィールドのみ更新
            if summary is not None:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if start_datetime is not None:
                event['start']['dateTime'] = start_datetime
            if end_datetime is not None:
                event['end']['dateTime'] = end_datetime

            updated_event = self.service.events().update(
                calendarId=calendar_id, eventId=event_id, body=event).execute()

            print(f"イベントが更新されました: {updated_event.get('htmlLink')}")
            return True
            
        except HttpError as error:
            print(f"Googleカレンダーイベント更新エラー: {error}")
            return False
        except Exception as error:
            print(f"イベント更新エラー: {error}")
            return False

    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """
        イベントを削除
        
        Args:
            event_id: 削除するイベントのID
            calendar_id: カレンダーID
            
        Returns:
            削除成功時True、失敗時False
        """
        try:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id).execute()
            print("イベントが削除されました。")
            return True
            
        except HttpError as error:
            print(f"Googleカレンダーイベント削除エラー: {error}")
            return False
        except Exception as error:
            print(f"イベント削除エラー: {error}")
            return False

    def get_calendar_list(self) -> List[Dict[str, str]]:
        """
        利用可能なカレンダーのリストを取得
        
        Returns:
            カレンダー情報のリスト
        """
        try:
            calendar_list = self.service.calendarList().list().execute()
            
            calendars = []
            for calendar in calendar_list.get('items', []):
                calendars.append({
                    'id': calendar['id'],
                    'summary': calendar['summary'],
                    'primary': calendar.get('primary', False)
                })
            
            return calendars
            
        except HttpError as error:
            print(f"カレンダーリスト取得エラー: {error}")
            return []
        except Exception as error:
            print(f"カレンダーリスト取得エラー: {error}")
            return []