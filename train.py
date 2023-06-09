import argparse
import json
import os
import random
import csv
from typing import List
import telegram

import numpy as np
import torch
import asyncio


from module.trainer import LearningEnv
from module.model_setting import ENCODER_NAME, UNFREEZE
from dotenv import load_dotenv


def set_random_seed(seed: int):
    random_seed = seed
    torch.manual_seed(random_seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    np.random.seed(random_seed)
    random.seed(random_seed)
    torch.cuda.manual_seed(random_seed)
    torch.cuda.manual_seed_all(random_seed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='This code is for ECPE task.')

    # Training Environment
    parser.add_argument('--gpus', default=[0,1,2])
    parser.add_argument('--num_process', default=int(os.cpu_count() * 0.8), type=int)
    parser.add_argument('--num_worker', default=6, type=int)
    parser.add_argument('--port', default=1234, type=int)

    parser.add_argument('--model_name', default='PRG_MoE')
    parser.add_argument('--pretrained_model', default=None)
    parser.add_argument('--test', default=False)

    parser.add_argument('--split_directory', default=None)
    parser.add_argument('--train_data', default="data/data_fold/data_0/dailydialog_train.json")
    parser.add_argument('--valid_data', default="data/data_fold/data_0/dailydialog_valid.json")
    parser.add_argument('--test_data', default="data/data_fold/data_0/dailydialog_test.json")
    parser.add_argument('--log_directory', default='logs', type=str)
    parser.add_argument('--data_label', help='the label that attaches to saved model', default='dailydialog_fold_0')

    parser.add_argument('--dropout', default=0.5, type=float)
    parser.add_argument('--n_speaker', help='the number of speakers', default=2, type=int)
    parser.add_argument('--n_emotion', help='the number of emotions', default=7, type=int)
    parser.add_argument('--n_cause', help='the number of causes', default=2, type=int)
    parser.add_argument('--n_expert', help='the number of causes', default=4, type=int)
    parser.add_argument('--guiding_lambda', help='the mixing ratio', default=0.6, type=float)

    parser.add_argument('--max_seq_len', help='the max length of each tokenized utterance', default=75, type=int)
    parser.add_argument('--contain_context', help='While tokenizing, previous utterances are contained or not', default=False)

    parser.add_argument('--training_iter', default=5, type=int)
    parser.add_argument('--batch_size', default=5, type=int)
    parser.add_argument('--learning_rate', default=5e-5, type=float)
    parser.add_argument('--patience', help='patience for Early Stopping', default=None, type=int)

    return parser.parse_args()


def test_preconditions(args: argparse.Namespace):
    if args.test:
        assert args.pretrained_model is not None, "For test, you should load pretrained model."


def main():
    load_dotenv()
    args = parse_args()
    test_preconditions(args)
    set_random_seed(77)

    os.environ["CUDA_VISIBLE_DEVICES"] = ",".join([str(_) for _ in args.gpus])
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # ignore TF error message 
    
    # train_data_list = [
    #     'data/data_fold/data_0/dailydialog_train.json',
    #     * [f'data/data_fold/data_{fold_}/data_{fold_}_train.json' for fold_ in range(1, 5)]
    # ]
    # valid_data_list = [
    #     'data/data_fold/data_0/dailydialog_valid.json',
    #     * [f'data/data_fold/data_{fold_}/data_{fold_}_valid.json' for fold_ in range(1, 5)]
    # ]
    # test_data_list = [
    #     'data/data_fold/data_0/dailydialog_test.json',
    #     * [f'data/data_fold/data_{fold_}/data_{fold_}_test.json' for fold_ in range(1, 5)]
    # ]
    # data_label = ['-original_data_DailyDialog', *[f'-data_{fold_}_DailyDialog' for fold_ in range(1, 5)]]
    
    # Original Dataset (1 fold)
    train_data_list = ['data/data_fold/data_0/dailydialog_train.json']
    valid_data_list = ['data/data_fold/data_0/dailydialog_valid.json']
    test_data_list = ['data/data_fold/data_0/dailydialog_test.json']
    data_label = ['-original_fold']
    
    # # Another folds
    # fold_ = 2
    # train_data_list = [
    #     * [f'data/data_fold/data_{fold_}/data_{fold_}_train.json']
    # ]
    # valid_data_list = [
    #     * [f'data/data_fold/data_{fold_}/data_{fold_}_valid.json']
    # ]
    # test_data_list = [
    #     * [f'data/data_fold/data_{fold_}/data_{fold_}_test.json']
    # ]
    # data_label = [* [f'-data_{fold_}_DailyDialog']]
    
    # # Mini Dataset (1 fold)
    # train_data_list = ['data/data_mini/dailydialog_train.json']
    # valid_data_list = ['data/data_mini/dailydialog_valid.json']
    # test_data_list = ['data/data_mini/dailydialog_test.json']
    # data_label = ['-original_mini']
    
    # 텔레그램 봇 설정
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    CHAT_ID = os.getenv('CHAT_ID')
    # bot = telegram.Bot(token=BOT_TOKEN)
    chat_id = CHAT_ID
    
    lrs = [5e-6]

    model_name_list = ['PRG_MoE_General']
    log_directory_list = ['logs/train_PRG_MoE_General(bert-base-unfreezed 3)']
    
    encoder_name = ENCODER_NAME.replace('/', '_')

    for tr, va, te, dl in zip(train_data_list, valid_data_list, test_data_list, data_label):
        args.train_data, args.valid_data, args.test_data, args.data_label = tr, va, te, dl

        for mo, log_d in zip(model_name_list, log_directory_list):
            for lr in lrs:
                # 학습 시작 알림
                # asyncio.run(bot.sendMessage(chat_id=chat_id, text=f'Training Start!\ntrain_{lr}_{encoder_name}, Unfreze{UNFREEZE}\ndata: {dl}'))
                
                args.learning_rate = lr
                args.model_name = mo
                if args.pretrained_model is None:
                    args.log_directory = f'logs/train_{lr}_{encoder_name}-{dl}, Unfreze{UNFREEZE}'#_({args.pretrained_model[6:-3]})'
                else:
                    args.log_directory = f'logs/test_(1gpu)_new_metric_{args.pretrained_model[6:-3]})' # test인 경우
                
                # args.log_directory = log_d + dl

                trainer = LearningEnv(**vars(args))
                trainer.run(**vars(args))

                del trainer
                
                if (args.test):
                    break
            
                # 현재 설정의 학습 완료를 알림
                # asyncio.run(bot.sendMessage(chat_id=chat_id, text=f'Training is done!\ntrain_{lr}_{encoder_name}, Unfreze{UNFREEZE}\ndata: {dl}'))
    
    # train_data_list = [f'data_fold_test_IEMOCAP/data_{fold_}/data_{fold_}_train.json' for fold_ in range(0, 5)]
    # valid_data_list = [f'data_fold_test_IEMOCAP/data_{fold_}/data_{fold_}_valid.json' for fold_ in range(0, 5)]
    # test_data_list = [f'data_fold_test_IEMOCAP/data_{fold_}/data_{fold_}_test.json' for fold_ in range(0, 5)]
    # data_label = [f'-data_{fold_}_IEMOCAP' for fold_ in range(0, 5)]

    # for tr, va, te, dl in zip(train_data_list, valid_data_list, test_data_list, data_label):
    #     args.train_data, args.valid_data, args.test_data, args.data_label = tr, va, te, dl

    #     for mo, log_d in zip(model_name_list, log_directory_list):
    #         args.model_name = mo
    #         args.log_directory = log_d + dl

    #         trainer = LearningEnv(**vars(args))
    #         trainer.run(**vars(args))

    #         del trainer


if __name__ == "__main__":
    main()
