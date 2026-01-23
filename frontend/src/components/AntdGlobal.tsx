import { App } from 'antd';
import type { MessageInstance } from 'antd/es/message/interface';
import type { ModalStaticFunctions } from 'antd/es/modal/interface';
import type { NotificationInstance } from 'antd/es/notification/interface';

// 初始导出为空对象，避免在组件挂载前调用报错
let message: MessageInstance = {} as MessageInstance;
let notification: NotificationInstance = {} as NotificationInstance;
let modal: ModalStaticFunctions = {} as ModalStaticFunctions;

/**
 * 这是一个内部组件，用于从 Ant Design 的 <App> 组件中获取实例
 */
export const AntdGlobal = () => {
    const staticFunction = App.useApp();
    message = staticFunction.message;
    modal = staticFunction.modal;
    notification = staticFunction.notification;
    return null;
};

// 重新导出实例，以便在全站直接引用
export { message, notification, modal };
