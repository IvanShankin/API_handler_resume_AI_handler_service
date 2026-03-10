import json
from logging import Logger

from openai import AsyncOpenAI, RateLimitError, PermissionDeniedError

from src.schemas.ai_handler import AIHandlerResult, AIResponse
from src.schemas.kafka_data import NewProcessing, EndProcessing
from src.service.ai_handler.limits import LimitAiRequest
from src.service.config.schemas import Config
from src.service.kafka.producer_sevice import KafkaProducerService


class AiHandlerService:

    def __init__(self, producer: KafkaProducerService, limits: LimitAiRequest, conf: Config, logger: Logger):
        self.producer = producer
        self.limits = limits
        self.conf = conf
        self.logger = logger

        self.client = AsyncOpenAI(
            api_key=conf.env.yandex_cloud_api_key,
            base_url="https://ai.api.cloud.yandex.net/v1",
            project=conf.env.yandex_cloud_folder_id,
        )


    async def _run_handler(self, resume: str, requirements: str) -> AIHandlerResult:
        prompt = self.conf.prompt + f"Требования к вакансии: {requirements} \nКандидат:{resume}"

        limit = await self.limits.check_limits(prompt)
        if not limit.result:  # если превышен лимит
            return AIHandlerResult(
                success=False,
                response=None,
                message_error=limit.message,
                wait_seconds=limit.wait_seconds,
            )

        try:
            self.logger.info("Начата обработка запроса")
            response = await self.client.responses.create(
                model=self.conf.ai_model,
                input=prompt,
                temperature=0
            )
            self.logger.info("Обработка завершена без ошибок")
        except PermissionDeniedError:
            self.logger.exception('Сервер не должен отправлять запросы к GPT с Российского IP!')
            return AIHandlerResult(
                success=False,
                response=None,
                message_error='Сервер не должен отправлять запросы к GPT с Российского IP!',
                wait_seconds=None,
            )
        except RateLimitError as e:
            self.logger.error(f'Получили rate limit как ошибку!. {str(e)}')
            return AIHandlerResult(
                success=False,
                response=None,
                message_error='Пожалуйста подождите 20 секунд',
                wait_seconds=None,
            )
        except Exception as e:
            self.logger.exception(f'Неожиданная ошибка при запросе к OpenAI: {str(e)}')
            return AIHandlerResult(
                success=False,
                response=None,
                message_error='Произошла внутренняя ошибка',
                wait_seconds=None,
            )

        content = response.output_text
        self.limits.add_token_minutes(limit.prompt_tokens)

        cleaned_response = content.replace('```json', '').replace('```', '').strip()
        response_json = json.loads(cleaned_response)

        return AIHandlerResult(
            success=True,
            response=AIResponse(**response_json),
            message_error=None,
            wait_seconds=None,
        )

    async def start_processing(self, processing_data: NewProcessing):

        response_ai = await self._run_handler(
            resume=processing_data.resume,
            requirements=processing_data.requirement
        )

        await self.producer.send_finish_processing(
            data=EndProcessing(
                processing_id=processing_data.processing_id,
                success=response_ai.success,
                message_error=response_ai.message_error,
                wait_seconds=response_ai.wait_seconds,
                score=response_ai.response.score,
                matches=response_ai.response.matches,
                recommendation=response_ai.response.recommendation,
                verdict=response_ai.response.verdict,
            )
        )



